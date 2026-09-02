from strands import tool

from vendorops_agent.db import INVENTORY_TABLE
from vendorops_agent.tools._shared import _table


@tool
def get_inventory_status(sku: str) -> dict:
    """Look up our own stock for a SKU: quantity on hand, reorder threshold, and
    reorder quantity. Use this before deciding whether a SKU needs reordering."""
    item = _table(INVENTORY_TABLE).get_item(Key={"sku": sku}).get("Item")
    if item is None:
        return {"found": False, "sku": sku}
    return {"found": True, **item}
