import os

from strands.telemetry import StrandsTelemetry


def setup_telemetry() -> StrandsTelemetry:
    telemetry = StrandsTelemetry()
    if os.environ.get("ENABLE_OTLP_EXPORT", "").strip().lower() in ("1", "true", "yes"):
        telemetry.setup_otlp_exporter()
    return telemetry
