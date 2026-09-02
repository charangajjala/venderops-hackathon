from datetime import datetime, timezone
from uuid import uuid4

from strands import tool

from vendorops_agent.db import (
    BUYER_EMAIL,
    INVENTORY_TABLE,
    OPEN_RFQS_TABLE,
    PURCHASE_ORDERS_TABLE,
    QUOTES_TABLE,
    RFQS_TABLE,
    SES_SENDER_ADDRESS,
    VENDORS_TABLE,
    dynamodb_resource,
    ses_client,
    vendor_stock_table_name,
)


def _table(name: str):
    return dynamodb_resource().Table(name)


def _send_email(to_address: str, subject: str, body: str) -> dict:
    if not to_address:
        return {"sent": False, "reason": "no recipient address given"}
    try:
        ses_client().send_email(
            Source=SES_SENDER_ADDRESS,
            Destination={"ToAddresses": [to_address]},
            Message={
                "Subject": {"Data": subject},
                "Body": {"Text": {"Data": body}},
            },
        )
        return {"sent": True, "to": to_address}
    except Exception as exc:
        return {"sent": False, "reason": str(exc)}


@tool
def get_inventory_status(sku: str) -> dict:
    """Look up our own stock for a SKU: quantity on hand, reorder threshold, and
    reorder quantity. Use this before deciding whether a SKU needs reordering."""
    item = _table(INVENTORY_TABLE).get_item(Key={"sku": sku}).get("Item")
    if item is None:
        return {"found": False, "sku": sku}
    return {"found": True, **item}


@tool
def list_candidate_vendors(sku: str) -> list[dict]:
    """List approved vendors ranked by trust and reliability, most preferred
    first. Doesn't check whether a given vendor actually has stock of this SKU
    - call check_vendor_stock on each candidate in order until one has enough."""
    items = _table(VENDORS_TABLE).scan().get("Items", [])
    approved = [v for v in items if v.get("onboarding_status") == "approved"]
    approved.sort(
        key=lambda v: (bool(v.get("trusted")), float(v.get("reliability_score", 0))),
        reverse=True,
    )
    return approved


@tool
def get_vendor(vendor_id: str) -> dict:
    """Look up a single vendor's record - name, contact_email, trusted status,
    reliability_score. Use this when processing a vendor's reply to know who
    they are and whether they're trusted enough to auto-approve a PO for."""
    item = _table(VENDORS_TABLE).get_item(Key={"vendor_id": vendor_id}).get("Item")
    if item is None:
        return {"found": False, "vendor_id": vendor_id}
    return {"found": True, **item}


@tool
def check_vendor_stock(vendor_id: str, sku: str, quantity: int) -> dict:
    """Check whether a specific vendor has enough simulated stock of a SKU to
    fulfill the requested quantity. A vendor with no row for this SKU, or not
    enough quantity, is not fulfillable as-is - try the next candidate vendor
    rather than sending an RFQ to a vendor who can't cover it."""
    table_name = vendor_stock_table_name(vendor_id)
    item = _table(table_name).get_item(Key={"sku": sku}).get("Item")

    if item is None:
        return {
            "vendor_id": vendor_id,
            "sku": sku,
            "sufficient": False,
            "reason": f"vendor {vendor_id} has no stock record for {sku}",
        }

    available = int(item.get("quantity_available", 0))
    if available < quantity:
        return {
            "vendor_id": vendor_id,
            "sku": sku,
            "sufficient": False,
            "quantity_available": available,
            "reason": f"vendor {vendor_id} only has {available} of {sku}, need {quantity}",
        }

    return {
        "vendor_id": vendor_id,
        "sku": sku,
        "sufficient": True,
        "quantity_available": available,
    }


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
    vendor's quote, use notify_buyer to escalate instead - do not call this."""
    rfq = _table(RFQS_TABLE).get_item(Key={"rfq_id": rfq_id}).get("Item")
    if rfq is None:
        return {"created": False, "reason": f"no RFQ found for rfq_id {rfq_id}"}

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
    _table(RFQS_TABLE).update_item(
        Key={"rfq_id": rfq_id},
        UpdateExpression="SET #s = :s",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":s": "awarded"},
    )
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
