from datetime import datetime, timezone
from uuid import uuid4

from strands import tool

from vendorops_agent.db import (
    INVENTORY_TABLE,
    OPEN_RFQS_TABLE,
    RFQS_TABLE,
    SES_SENDER_ADDRESS,
    VENDORS_TABLE,
    dynamodb_resource,
    ses_client,
    vendor_stock_table_name,
)


def _table(name: str):
    return dynamodb_resource().Table(name)


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


def _send_rfq_email(rfq_id: str, sku: str, quantity: int, vendor: dict) -> dict:
    contact_email = vendor.get("contact_email")
    if not contact_email:
        return {"sent": False, "reason": f"vendor {vendor.get('vendor_id')} has no contact_email on file"}

    vendor_name = vendor.get("name", vendor.get("vendor_id"))
    body = (
        f"Hi {vendor_name},\n\n"
        f"We'd like to request a quote for the following:\n\n"
        f"  SKU: {sku}\n"
        f"  Quantity: {quantity}\n\n"
        f"Please reply to this email with your price, lead time, and MOQ.\n\n"
        f"Reference: RFQ {rfq_id}\n"
    )

    try:
        ses_client().send_email(
            Source=SES_SENDER_ADDRESS,
            Destination={"ToAddresses": [contact_email]},
            Message={
                "Subject": {"Data": f"RFQ {rfq_id[:8]} - {sku} x{quantity}"},
                "Body": {"Text": {"Data": body}},
            },
        )
        return {"sent": True, "to": contact_email}
    except Exception as exc:
        return {"sent": False, "reason": str(exc)}


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

    email_result = _send_rfq_email(rfq_id, sku, quantity, vendor)

    return {"created": True, "email": email_result, **rfq}
