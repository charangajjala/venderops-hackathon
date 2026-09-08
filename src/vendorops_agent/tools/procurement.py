from datetime import datetime, timezone
from uuid import uuid4

from botocore.exceptions import ClientError
from strands import tool

from vendorops_agent.db import (
    BUYER_EMAIL,
    OPEN_RFQS_TABLE,
    PURCHASE_ORDERS_TABLE,
    QUOTES_TABLE,
    RFQS_TABLE,
    VENDORS_TABLE,
)
from vendorops_agent.tools._shared import _send_email, _table


@tool
def create_rfq(sku: str, quantity: int, vendor_id: str) -> dict:
    """Create an RFQ for a SKU against a vendor who has confirmed sufficient
    stock, mark it as the SKU's open RFQ, and email the vendor's contact
    address requesting a quote. If this SKU already has an open RFQ, returns
    that existing one instead of creating a duplicate or sending another
    email."""
    open_rfqs = _table(OPEN_RFQS_TABLE)
    existing = open_rfqs.get_item(Key={"sku": sku}).get("Item")
    if existing is not None:
        return {"created": False, "reason": "an RFQ is already open for this SKU", **existing}

    vendor = _table(VENDORS_TABLE).get_item(Key={"vendor_id": vendor_id}).get("Item") or {
        "vendor_id": vendor_id
    }

    rfq_id = str(uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    rfq = {
        "rfq_id": rfq_id,
        "sku": sku,
        "quantity": quantity,
        "vendor_id": vendor_id,
        "status": "sent",
        "created_at": created_at,
    }

    _table(RFQS_TABLE).put_item(Item=rfq)
    open_rfqs.put_item(Item={"sku": sku, "rfq_id": rfq_id, "vendor_id": vendor_id})

    vendor_name = vendor.get("name", vendor_id)
    body = (
        f"Hi {vendor_name},\n\n"
        f"We'd like to request a quote for the following:\n\n"
        f"  SKU: {sku}\n"
        f"  Quantity: {quantity}\n\n"
        f"Please reply to this email with your price, lead time, and MOQ.\n\n"
        f"Reference: RFQ {rfq_id}\n"
    )
    email_result = _send_email(vendor.get("contact_email"), f"RFQ {rfq_id} - {sku} x{quantity}", body)

    return {"created": True, "email": email_result, **rfq}


@tool
def get_rfq(rfq_id: str) -> dict:
    """Look up an RFQ by its full id - use this when a vendor's reply
    references an RFQ id, to get the SKU/quantity/status it was for."""
    item = _table(RFQS_TABLE).get_item(Key={"rfq_id": rfq_id}).get("Item")
    if item is None:
        return {"found": False, "rfq_id": rfq_id}
    return {"found": True, **item}


@tool
def record_quote(
    rfq_id: str,
    vendor_id: str,
    unit_price: float,
    quantity: int,
    lead_time_days: int,
    moq: int | None = None,
    warranty_terms: str | None = None,
) -> dict:
    """Record a vendor's quote reply to an RFQ. Call this once you've read the
    price/quantity/lead time out of the vendor's email, before deciding
    whether to auto-approve or escalate."""
    quote_id = str(uuid4())
    quote = {
        "quote_id": quote_id,
        "rfq_id": rfq_id,
        "vendor_id": vendor_id,
        "unit_price": str(unit_price),
        "quantity": quantity,
        "lead_time_days": lead_time_days,
        "moq": moq,
        "warranty_terms": warranty_terms,
        "received_at": datetime.now(timezone.utc).isoformat(),
    }
    _table(QUOTES_TABLE).put_item(Item={k: v for k, v in quote.items() if v is not None})
    return quote


@tool
def create_purchase_order(rfq_id: str, quote_id: str, vendor_id: str, unit_price: float, quantity: int) -> dict:
    """Issue a purchase order from an approved quote: only call this for a
    trusted vendor's quote. Writes the PO, marks the RFQ awarded, closes the
    SKU's open-RFQ slot (so a future threshold crossing can trigger a fresh
    reorder), and emails the vendor a PO confirmation. For an untrusted
    vendor's quote, use notify_buyer to escalate instead - do not call this.
    If a PO was already issued for this RFQ (e.g. a retried call), returns
    without creating a second one."""
    rfq_table = _table(RFQS_TABLE)
    rfq = rfq_table.get_item(Key={"rfq_id": rfq_id}).get("Item")
    if rfq is None:
        return {"created": False, "reason": f"no RFQ found for rfq_id {rfq_id}"}

    if rfq.get("status") == "awarded":
        return {"created": False, "reason": f"a purchase order was already issued for RFQ {rfq_id}"}

    try:
        rfq_table.update_item(
            Key={"rfq_id": rfq_id},
            UpdateExpression="SET #s = :awarded",
            ConditionExpression="attribute_not_exists(#s) OR #s <> :awarded",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":awarded": "awarded"},
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return {
                "created": False,
                "reason": f"a purchase order was already issued for RFQ {rfq_id} (concurrent claim)",
            }
        raise

    vendor = _table(VENDORS_TABLE).get_item(Key={"vendor_id": vendor_id}).get("Item") or {
        "vendor_id": vendor_id
    }

    po_id = str(uuid4())
    total_price = unit_price * quantity
    po = {
        "po_id": po_id,
        "rfq_id": rfq_id,
        "quote_id": quote_id,
        "vendor_id": vendor_id,
        "sku": rfq.get("sku"),
        "quantity": quantity,
        "unit_price": str(unit_price),
        "total_price": str(total_price),
        "status": "issued",
        "issued_at": datetime.now(timezone.utc).isoformat(),
    }
    _table(PURCHASE_ORDERS_TABLE).put_item(Item=po)
    if rfq.get("sku"):
        _table(OPEN_RFQS_TABLE).delete_item(Key={"sku": rfq["sku"]})

    vendor_name = vendor.get("name", vendor_id)
    body = (
        f"Hi {vendor_name},\n\n"
        f"Confirming purchase order for {quantity} x {rfq.get('sku')} at "
        f"${unit_price}/unit (total ${total_price}).\n\n"
        f"PO reference: {po_id}\n"
    )
    email_result = _send_email(vendor.get("contact_email"), f"PO {po_id} confirmation", body)

    return {"created": True, "email": email_result, **po}


@tool
def notify_buyer(subject: str, body: str) -> dict:
    """Send a short escalation notification to the buyer - use this when a
    tradeoff or anomaly needs a human decision (e.g. an untrusted vendor's
    quote came in), instead of auto-issuing a purchase order."""
    return _send_email(BUYER_EMAIL, subject, body)
