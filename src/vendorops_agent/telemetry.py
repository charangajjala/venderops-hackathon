"""Strands OpenTelemetry setup for traces exported to the local collector."""

from __future__ import annotations

from strands.telemetry import StrandsTelemetry


def setup_telemetry() -> StrandsTelemetry:
    """Initialize the global Strands tracer and export spans over OTLP.

    Endpoint and service name come from OTEL_EXPORTER_OTLP_ENDPOINT and
    OTEL_SERVICE_NAME (set in Docker Compose / the process environment).
    """
    telemetry = StrandsTelemetry()
    telemetry.setup_otlp_exporter()
    return telemetry
