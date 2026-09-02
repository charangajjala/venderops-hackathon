"""Strands OpenTelemetry setup for traces exported to the local collector."""

from __future__ import annotations

import os

from strands.telemetry import StrandsTelemetry


def setup_telemetry() -> StrandsTelemetry:
    """Initialize the global Strands tracer, exporting spans over OTLP only if
    OTEL_EXPORTER_OTLP_ENDPOINT is actually set (Docker Compose sets this to
    the local collector). Without it, the OTLP SDK defaults to localhost:4318
    and retries with growing backoff on every export - fine locally, but on
    AgentCore Runtime (no collector sidecar) that alone added ~50s per
    invocation, enough to blow past callers' timeouts."""
    telemetry = StrandsTelemetry()
    if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        telemetry.setup_otlp_exporter()
    return telemetry
