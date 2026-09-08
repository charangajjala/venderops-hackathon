import argparse
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vendorops_agent.db import INVENTORY_TABLE, dynamodb_resource


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate a checkout sale decrementing stock.")
    parser.add_argument("sku")
    parser.add_argument("quantity", type=int, help="Units sold in this simulated sale.")
    args = parser.parse_args()

    table = dynamodb_resource().Table(INVENTORY_TABLE)
    item = table.get_item(Key={"sku": args.sku}).get("Item")
    if item is None:
        raise SystemExit(f"no Inventory item for sku={args.sku!r} - seed it first")

    current = int(item["quantity_on_hand"])
    new_quantity = max(current - args.quantity, 0)

    table.update_item(
        Key={"sku": args.sku},
        UpdateExpression="SET quantity_on_hand = :q",
        ExpressionAttributeValues={":q": Decimal(new_quantity)},
    )

    threshold = int(item.get("reorder_threshold", 0))
    crossed = current >= threshold > new_quantity
    print(f"{args.sku}: {current} -> {new_quantity} (threshold {threshold})")
    if crossed:
        print("crossed below reorder_threshold - Reorder Checker Lambda should fire")


if __name__ == "__main__":
    main()
