import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vendorops_agent.db import (
    INVENTORY_TABLE,
    VENDORS_TABLE,
    dynamodb_resource,
    vendor_stock_table_name,
)

SKU = "milk-1l-organic"

VENDORS = [
    {
        "vendor_id": "cascade-packaging",
        "name": "Cascade Packaging Co",
        "onboarding_status": "approved",
        "trusted": True,
        "reliability_score": Decimal("0.9"),
        "location": "Portland, OR",
        "stock": {SKU: 0},
    },
    {
        "vendor_id": "green-valley-dairy",
        "name": "Green Valley Dairy",
        "onboarding_status": "approved",
        "trusted": True,
        "reliability_score": Decimal("0.85"),
        "location": "Madison, WI",
        "stock": {SKU: 200},
    },
    {
        "vendor_id": "sunrise-farms",
        "name": "Sunrise Farms",
        "onboarding_status": "approved",
        "trusted": False,
        "reliability_score": Decimal("0.5"),
        "location": "Fresno, CA",
        "stock": {SKU: 150},
    },
]


def main() -> None:
    resource = dynamodb_resource()

    inventory = resource.Table(INVENTORY_TABLE)
    inventory.put_item(
        Item={
            "sku": SKU,
            "quantity_on_hand": Decimal("15"),
            "reorder_threshold": Decimal("20"),
            "reorder_quantity": Decimal("100"),
        }
    )
    print(f"seeded Inventory: {SKU} at 15/20 (below threshold)")

    vendors_table = resource.Table(VENDORS_TABLE)
    for vendor in VENDORS:
        stock = vendor.pop("stock")
        vendors_table.put_item(Item=vendor)
        print(f"seeded Vendors: {vendor['vendor_id']} (trusted={vendor['trusted']})")

        stock_table = resource.Table(vendor_stock_table_name(vendor["vendor_id"]))
        for sku, quantity_available in stock.items():
            stock_table.put_item(
                Item={"sku": sku, "quantity_available": Decimal(quantity_available)}
            )
        print(f"seeded VendorStock-{vendor['vendor_id']}: {stock}")


if __name__ == "__main__":
    main()
