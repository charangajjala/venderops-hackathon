import email
import json
import os
import re
from datetime import datetime, timedelta, timezone

import boto3

s3 = boto3.client("s3")
agentcore = boto3.client("bedrock-agentcore")
dynamodb = boto3.resource("dynamodb")

RAW_EMAILS_BUCKET = os.environ["RAW_EMAILS_BUCKET"]
RAW_EMAILS_PREFIX = os.environ.get("RAW_EMAILS_PREFIX", "inbound")
AGENT_RUNTIME_ARN = os.environ["AGENT_RUNTIME_ARN"]
IDEMPOTENCY_TABLE = os.environ["IDEMPOTENCY_TABLE"]
IDEMPOTENCY_TTL_DAYS = int(os.environ.get("IDEMPOTENCY_TTL_DAYS", "30"))

RFQ_ID_RE = re.compile(r"RFQ ([0-9a-fA-F-]{36})")


def _subject(notification: dict) -> str:
    common = notification.get("mail", {}).get("commonHeaders", {})
    if common.get("subject"):
        return common["subject"]
    for header in notification.get("mail", {}).get("headers", []):
        if header.get("name", "").lower() == "subject":
            return header.get("value", "")
    return ""


def _extract_body(raw_bytes: bytes) -> str:
    msg = email.message_from_bytes(raw_bytes)
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.get_filename():
                charset = part.get_content_charset() or "utf-8"
                return part.get_payload(decode=True).decode(charset, errors="replace")
        return ""
    charset = msg.get_content_charset() or "utf-8"
    return msg.get_payload(decode=True).decode(charset, errors="replace")


def _session_id(message_id: str) -> str:
    return f"reply-{message_id}".ljust(33, "0")[:256]


def handler(event, context):
    idempotency = dynamodb.Table(IDEMPOTENCY_TABLE)
    processed = []

    for record in event.get("Records", []):
        try:
            notification = json.loads(record["body"])
        except (KeyError, json.JSONDecodeError):
            print("skip: message body is not JSON")
            continue

        if notification.get("notificationType") != "Received":
            continue

        message_id = notification.get("mail", {}).get("messageId")
        if not message_id or message_id == "AMAZON_SES_SETUP_NOTIFICATION":
            continue

        if idempotency.get_item(Key={"message_id": message_id}).get("Item"):
            print(f"skip {message_id}: already processed")
            continue

        sender = notification.get("mail", {}).get("source", "")
        subject = _subject(notification)

        s3_key = f"{RAW_EMAILS_PREFIX}/{message_id}"
        obj = s3.get_object(Bucket=RAW_EMAILS_BUCKET, Key=s3_key)
        body = _extract_body(obj["Body"].read())

        rfq_match = RFQ_ID_RE.search(subject) or RFQ_ID_RE.search(body)
        rfq_id = rfq_match.group(1) if rfq_match else None

        prompt = (
            f"An email reply arrived from {sender}, subject: {subject!r}. "
            + (f"It references RFQ {rfq_id}. " if rfq_id else "It doesn't clearly reference an RFQ id. ")
            + "Message body:\n\n"
            + body
            + "\n\nIf this is a vendor's quote reply to an open RFQ, follow the "
            "reply-processing steps in your instructions."
        )

        response = agentcore.invoke_agent_runtime(
            agentRuntimeArn=AGENT_RUNTIME_ARN,
            runtimeSessionId=_session_id(message_id),
            contentType="application/json",
            accept="application/json",
            payload=json.dumps({"prompt": prompt}).encode("utf-8"),
        )
        print(f"invoked agent for reply from {sender}: status={response.get('statusCode')}")

        expires_at = int((datetime.now(timezone.utc) + timedelta(days=IDEMPOTENCY_TTL_DAYS)).timestamp())
        idempotency.put_item(Item={"message_id": message_id, "expires_at": expires_at})
        processed.append(message_id)

    return {"processed": processed}
