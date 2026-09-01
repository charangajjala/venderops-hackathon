import logging
import os
from pathlib import Path

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.runtime.context import BedrockAgentCoreContext
from dotenv import load_dotenv
from strands import Agent
from strands.models import BedrockModel
from strands.session.s3_session_manager import S3SessionManager

from vendorops_agent.db import AGENT_SESSIONS_BUCKET
from vendorops_agent.telemetry import setup_telemetry
from vendorops_agent.tools import (
    check_vendor_stock,
    create_rfq,
    get_inventory_status,
    list_candidate_vendors,
)

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


aws_region = (
    _env("AWS_REGION", required=False)
    or _env("AWS_DEFAULT_REGION", required=False)
    or "us-east-1"
)

MODEL_ID = "us.amazon.nova-micro-v1:0"

bedrock_model = BedrockModel(
    model_id=MODEL_ID,
    region_name=aws_region,
    temperature=0.4,
    streaming=False,
)

SYSTEM_PROMPT = (
    "You are a VendorOps agent for a supermarket. You help manage vendor "
    "operations: checking inventory, reordering low-stock SKUs, RFQs, quotes, "
    "MOQ, lead time, Incoterms, payment terms, purchase orders, change orders, "
    "partial shipments, RMAs, vendor onboarding, trusted-vendor status, and "
    "reliability scores. "
    "When a SKU needs reordering: call list_candidate_vendors to get vendors "
    "ranked by trust, then call check_vendor_stock on each in order until one "
    "has enough stock - do not send an RFQ to a vendor before confirming they "
    "can fulfill it. Once a vendor with sufficient stock is found, call "
    "create_rfq against that vendor. If no candidate vendor has enough stock, "
    "say so plainly rather than guessing or inventing availability. Be "
    "concise, accurate, and operational. When a request is ambiguous, ask a "
    "short clarifying question."
)

TOOLS = [get_inventory_status, list_candidate_vendors, check_vendor_stock, create_rfq]

app = BedrockAgentCoreApp()
agent = Agent(model=bedrock_model, system_prompt=SYSTEM_PROMPT, tools=TOOLS)


def _build_agent(session_id: str) -> Agent:
    session_manager = S3SessionManager(
        session_id=session_id,
        bucket=AGENT_SESSIONS_BUCKET,
        prefix="vendorops-sessions",
        region_name=aws_region,
    )
    return Agent(
        model=bedrock_model,
        system_prompt=SYSTEM_PROMPT,
        tools=TOOLS,
        session_manager=session_manager,
    )


@app.entrypoint
def invoke(payload):
    """Process user input and return a response."""
    user_message = payload.get("prompt", "Hello")
    session_id = BedrockAgentCoreContext.get_session_id() or "local-dev"
    logger.info("invoke session_id=%s prompt=%s", session_id, user_message[:200])
    session_agent = _build_agent(session_id)
    result = session_agent(user_message)
    telemetry.tracer_provider.force_flush(timeout_millis=5000)
    return {"result": result.message}
