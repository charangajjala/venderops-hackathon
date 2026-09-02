import json
import os

import boto3

dynamodb = boto3.resource("dynamodb")
agentcore = boto3.client("bedrock-agentcore")

OPEN_RFQS_TABLE = os.environ["OPEN_RFQS_TABLE"]
AGENT_RUNTIME_ARN = os.environ["AGENT_RUNTIME_ARN"]


def _to_number(attr):
    if not attr:
        return None
    value = attr.get("N")
    return float(value) if value is not None else None


def _session_id(sku: str) -> str:
    return f"reorder-{sku}".ljust(33, "0")[:256]


def handler(event, context):
    open_rfqs = dynamodb.Table(OPEN_RFQS_TABLE)
    invoked = []

    for record in event.get("Records", []):
        if record.get("eventName") not in ("INSERT", "MODIFY"):
            continue

        change = record.get("dynamodb", {})
        new_image = change.get("NewImage", {})
        old_image = change.get("OldImage", {})

        sku = new_image.get("sku", {}).get("S")
        if not sku:
            continue

        threshold = _to_number(new_image.get("reorder_threshold"))
        new_qty = _to_number(new_image.get("quantity_on_hand"))
        old_qty = _to_number(old_image.get("quantity_on_hand")) if old_image else None

        if threshold is None or new_qty is None:
            continue

        crossed_below = new_qty < threshold and (old_qty is None or old_qty >= threshold)
        if not crossed_below:
            continue

        if open_rfqs.get_item(Key={"sku": sku}).get("Item"):
            print(f"skip {sku}: RFQ already open for this SKU")
            continue

        reorder_quantity = _to_number(new_image.get("reorder_quantity")) or threshold

        prompt = (
            f"Inventory SKU {sku} has dropped to {new_qty}, below its reorder "
            f"threshold of {threshold}. Reorder {int(reorder_quantity)} units: check "
            f"candidate vendors ranked by trust, verify stock with each in order until "
            f"one has enough, and create an RFQ with that vendor."
        )

        response = agentcore.invoke_agent_runtime(
            agentRuntimeArn=AGENT_RUNTIME_ARN,
            runtimeSessionId=_session_id(sku),
            contentType="application/json",
            accept="application/json",
            payload=json.dumps({"prompt": prompt}).encode("utf-8"),
        )
        print(f"invoked agent for {sku}: status={response.get('statusCode')}")
        invoked.append(sku)

    return {"invoked": invoked}
