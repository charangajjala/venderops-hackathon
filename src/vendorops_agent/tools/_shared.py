from vendorops_agent.db import SES_SENDER_ADDRESS, dynamodb_resource, ses_client


def _table(name: str):
    return dynamodb_resource().Table(name)


def _send_email(to_address: str, subject: str, body: str) -> dict:
    if not to_address:
        return {"sent": False, "reason": "no recipient address given"}
    try:
        ses_client().send_email(
            Source=SES_SENDER_ADDRESS,
            Destination={"ToAddresses": [to_address]},
            Message={
                "Subject": {"Data": subject},
                "Body": {"Text": {"Data": body}},
            },
        )
        return {"sent": True, "to": to_address}
    except Exception as exc:
        return {"sent": False, "reason": str(exc)}
