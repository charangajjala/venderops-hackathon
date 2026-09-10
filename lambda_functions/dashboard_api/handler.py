import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")
ses = boto3.client("ses")

INVENTORY_TABLE = os.environ["INVENTORY_TABLE"]
VENDORS_TABLE = os.environ["VENDORS_TABLE"]
RFQS_TABLE = os.environ["RFQS_TABLE"]
OPEN_RFQS_TABLE = os.environ["OPEN_RFQS_TABLE"]
QUOTES_TABLE = os.environ["QUOTES_TABLE"]
PURCHASE_ORDERS_TABLE = os.environ["PURCHASE_ORDERS_TABLE"]
SES_SENDER_ADDRESS = os.environ.get("SES_SENDER_ADDRESS", "rfqs@pixelbuffer.club")
WRITE_API_KEY = os.environ.get("WRITE_API_KEY", "")

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,X-Api-Key",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
}


class _JsonEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return int(o) if o % 1 == 0 else float(o)
        return super().default(o)


def _response(status: int, body) -> dict:
    return {
        "statusCode": status,
        "headers": {**CORS_HEADERS, "Content-Type": "application/json"},
        "body": json.dumps(body, cls=_JsonEncoder),
    }


def _table(name: str):
    return dynamodb.Table(name)


def _send_email(to_address: str | None, subject: str, body: str) -> dict:
    if not to_address:
        return {"sent": False, "reason": "no contact_email on file"}
    ses.send_email(
        Source=SES_SENDER_ADDRESS,
        Destination={"ToAddresses": [to_address]},
        Message={
            "Subject": {"Data": subject},
            "Body": {"Text": {"Data": body}},
        },
    )
    return {"sent": True, "to": to_address}


def _list_inventory(event):
    items = _table(INVENTORY_TABLE).scan().get("Items", [])
    return _response(200, items)


def _list_vendors(event):
    items = _table(VENDORS_TABLE).scan().get("Items", [])
    return _response(200, items)


def _list_rfqs(event):
    rfqs = _table(RFQS_TABLE).scan().get("Items", [])
    quotes_table = _table(QUOTES_TABLE)
    for rfq in rfqs:
        quotes = quotes_table.scan(FilterExpression=Attr("rfq_id").eq(rfq["rfq_id"])).get("Items", [])
        rfq["quote"] = quotes[0] if quotes else None
    return _response(200, rfqs)


def _list_purchase_orders(event):
    items = _table(PURCHASE_ORDERS_TABLE).scan().get("Items", [])
    return _response(200, items)


def _authorized(event) -> bool:
    if not WRITE_API_KEY:
        return True
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    return headers.get("x-api-key") == WRITE_API_KEY


def _approve_rfq(event):
    if not _authorized(event):
        return _response(401, {"error": "unauthorized"})

    rfq_id = event["pathParameters"]["rfq_id"]
    rfq_table = _table(RFQS_TABLE)
    rfq = rfq_table.get_item(Key={"rfq_id": rfq_id}).get("Item")
    if rfq is None:
        return _response(404, {"error": f"no RFQ found for rfq_id {rfq_id}"})

    if rfq.get("status") == "awarded":
        return _response(409, {"error": f"a purchase order was already issued for RFQ {rfq_id}"})

    quotes = _table(QUOTES_TABLE).scan(FilterExpression=Attr("rfq_id").eq(rfq_id)).get("Items", [])
    if not quotes:
        return _response(400, {"error": f"no quote recorded for RFQ {rfq_id}"})
    quote = quotes[0]

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
            return _response(409, {"error": f"a purchase order was already issued for RFQ {rfq_id} (concurrent claim)"})
        raise

    vendor_id = quote["vendor_id"]
    vendor = _table(VENDORS_TABLE).get_item(Key={"vendor_id": vendor_id}).get("Item") or {"vendor_id": vendor_id}

    unit_price = Decimal(str(quote["unit_price"]))
    quantity = int(quote["quantity"])
    total_price = unit_price * quantity

    po_id = str(uuid4())
    po = {
        "po_id": po_id,
        "rfq_id": rfq_id,
        "quote_id": quote["quote_id"],
        "vendor_id": vendor_id,
        "sku": rfq.get("sku"),
        "quantity": quantity,
        "unit_price": str(unit_price),
        "total_price": str(total_price),
        "status": "issued",
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "approved_via": "dashboard",
    }
    _table(PURCHASE_ORDERS_TABLE).put_item(Item=po)
    if rfq.get("sku"):
        _table(OPEN_RFQS_TABLE).delete_item(Key={"sku": rfq["sku"]})
        _table(INVENTORY_TABLE).update_item(
            Key={"sku": rfq["sku"]},
            UpdateExpression="ADD quantity_on_hand :qty",
            ExpressionAttributeValues={":qty": quantity},
        )

    vendor_name = vendor.get("name", vendor_id)
    body = (
        f"Hi {vendor_name},\n\n"
        f"Confirming purchase order for {quantity} x {rfq.get('sku')} at "
        f"${unit_price}/unit (total ${total_price}).\n\n"
        f"PO reference: {po_id}\n"
    )
    email_result = _send_email(vendor.get("contact_email"), f"PO {po_id} confirmation", body)

    return _response(200, {"created": True, "email": email_result, **po})


def _reject_rfq(event):
    if not _authorized(event):
        return _response(401, {"error": "unauthorized"})

    rfq_id = event["pathParameters"]["rfq_id"]
    rfq_table = _table(RFQS_TABLE)
    rfq = rfq_table.get_item(Key={"rfq_id": rfq_id}).get("Item")
    if rfq is None:
        return _response(404, {"error": f"no RFQ found for rfq_id {rfq_id}"})

    rfq_table.update_item(
        Key={"rfq_id": rfq_id},
        UpdateExpression="SET #s = :rejected",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":rejected": "rejected"},
    )
    if rfq.get("sku"):
        _table(OPEN_RFQS_TABLE).delete_item(Key={"sku": rfq["sku"]})

    return _response(200, {"rejected": True, "rfq_id": rfq_id})


ROUTES = {
    "GET /inventory": _list_inventory,
    "GET /vendors": _list_vendors,
    "GET /rfqs": _list_rfqs,
    "GET /purchase-orders": _list_purchase_orders,
    "POST /rfqs/{rfq_id}/approve": _approve_rfq,
    "POST /rfqs/{rfq_id}/reject": _reject_rfq,
}


def handler(event, context):
    route_key = event.get("routeKey", "")
    if event.get("requestContext", {}).get("http", {}).get("method") == "OPTIONS":
        return _response(200, {})

    route = ROUTES.get(route_key)
    if route is None:
        return _response(404, {"error": f"no route for {route_key}"})

    return route(event)
