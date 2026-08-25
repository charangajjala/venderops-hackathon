import logging
import os
from pathlib import Path

import boto3
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from dotenv import load_dotenv
from strands import Agent
from strands.models import BedrockModel

from vendorops_agent.telemetry import setup_telemetry

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

telemetry = setup_telemetry()
logger = logging.getLogger("vendorops-agent")


def _env(name: str, *, required: bool = True) -> str | None:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    if required:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return None


aws_access_key_id = _env("AWS_ACCESS_KEY_ID")
aws_secret_access_key = _env("AWS_SECRET_ACCESS_KEY")
aws_session_token = _env("AWS_SESSION_TOKEN", required=False)
aws_region = _env("AWS_DEFAULT_REGION", required=False) or "us-east-1"

boto3.setup_default_session(
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    aws_session_token=aws_session_token,
    region_name=aws_region,
)

MODEL_ID = "us.amazon.nova-micro-v1:0"

bedrock_model = BedrockModel(
    model_id=MODEL_ID,
    temperature=0.4,
    streaming=False,
)

SYSTEM_PROMPT = (
    "You are a VendorOps agent. You help buyers manage vendor operations: "
    "RFQs, quotes, MOQ, lead time, Incoterms, payment terms, purchase orders, "
    "change orders, partial shipments, RMAs, vendor onboarding, trusted-vendor "
    "status, and reliability scores. Be concise, accurate, and operational. "
    "When a request is ambiguous, ask a short clarifying question."
)

app = BedrockAgentCoreApp()
agent = Agent(model=bedrock_model, system_prompt=SYSTEM_PROMPT)


@app.entrypoint
def invoke(payload):
    """Process user input and return a response."""
    user_message = payload.get("prompt", "Hello")
    logger.info("invoke prompt=%s", user_message[:200])
    result = agent(user_message)
    telemetry.tracer_provider.force_flush(timeout_millis=5000)
    return {"result": result.message}
