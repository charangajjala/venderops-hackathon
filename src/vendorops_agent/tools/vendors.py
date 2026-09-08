from strands import tool

from vendorops_agent.db import VENDORS_TABLE, vendor_stock_table_name
from vendorops_agent.tools._shared import _table


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
