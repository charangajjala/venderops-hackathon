from datetime import datetime, timezone
from uuid import uuid4

from strands import tool

from vendorops_agent.db import (
    INVENTORY_TABLE,
    OPEN_RFQS_TABLE,
    RFQS_TABLE,
    VENDORS_TABLE,
    dynamodb_resource,
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


@tool
def create_rfq(sku: str, quantity: int, vendor_id: str) -> dict:
    """Create an RFQ for a SKU against a vendor who has confirmed sufficient
    stock, and mark it as the SKU's open RFQ. If this SKU already has an open
    RFQ, returns that existing one instead of creating a duplicate."""
    open_rfqs = _table(OPEN_RFQS_TABLE)
    existing = open_rfqs.get_item(Key={"sku": sku}).get("Item")
    if existing is not None:
        return {"created": False, "reason": "an RFQ is already open for this SKU", **existing}

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

    return {"created": True, **rfq}
