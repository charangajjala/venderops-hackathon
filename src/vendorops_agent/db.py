import os

import boto3

_PROJECT = os.environ.get("PROJECT", "vendorops")
_ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")
_NAME_PREFIX = f"{_PROJECT}-{_ENVIRONMENT}"


def _table_name(env_var: str, default_suffix: str) -> str:
    return os.environ.get(env_var, f"{_NAME_PREFIX}-{default_suffix}")


INVENTORY_TABLE = _table_name("DYNAMODB_TABLE_INVENTORY", "Inventory")
VENDORS_TABLE = _table_name("DYNAMODB_TABLE_VENDORS", "Vendors")
RFQS_TABLE = _table_name("DYNAMODB_TABLE_RFQS", "RFQs")
OPEN_RFQS_TABLE = _table_name("DYNAMODB_TABLE_OPEN_RFQS", "OpenRFQs")
QUOTES_TABLE = _table_name("DYNAMODB_TABLE_QUOTES", "Quotes")
PURCHASE_ORDERS_TABLE = _table_name("DYNAMODB_TABLE_PURCHASE_ORDERS", "PurchaseOrders")
IDEMPOTENCY_TABLE = _table_name("DYNAMODB_TABLE_IDEMPOTENCY", "Idempotency")

VENDOR_STOCK_TABLE_PREFIX = os.environ.get(
    "VENDOR_STOCK_TABLE_PREFIX", f"{_NAME_PREFIX}-VendorStock-"
)

AGENT_SESSIONS_BUCKET = os.environ.get("AGENT_SESSIONS_BUCKET", f"{_NAME_PREFIX}-agent-sessions")

SES_SENDER_ADDRESS = os.environ.get("SES_SENDER_ADDRESS", "rfqs@pixelbuffer.club")
BUYER_EMAIL = os.environ.get("BUYER_EMAIL", "jampuramprem01@gmail.com")


def vendor_stock_table_name(vendor_id: str) -> str:
    return f"{VENDOR_STOCK_TABLE_PREFIX}{vendor_id}"


def _region() -> str:
    return os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"


def dynamodb_resource():
    return boto3.resource("dynamodb", region_name=_region())


def ses_client():
    return boto3.client("ses", region_name=_region())
