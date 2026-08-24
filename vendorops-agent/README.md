# vendorops-agent

VendorOps agent on Amazon Bedrock AgentCore, using Strands. Model: `us.amazon.nova-micro-v1:0`. Traces go through Strands `StrandsTelemetry` to the local OTLP collector.

## Setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.11.

```bash
cd vendorops-agent
uv sync
cp .env.example .env
```

Set `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_DEFAULT_REGION` in `.env`. Add `AWS_SESSION_TOKEN` if you use temporary credentials.

## Run without Docker

```bash
uv run vendorops-agent
```

or:

```bash
uv run python src/agent.py
```

## Local Docker stack

From `vendorops-agent` (preferred):

```bash
docker compose up --build --pull never -d
docker compose down
```

From the repo root:

```bash
make docker-run-local
make docker-stop-local
```

The agent image is `vendorops-agent:local` (`pull_policy: build`). AWS keys come from `env_file: .env`. Do not interpolate empty `${AWS_*}` values in Compose; that overwrites the file.

### Invoke

PowerShell mangles JSON on the command line. Write the body to a file:

```powershell
Set-Content $env:TEMP\hi.json '{"prompt":"Hi"}' -NoNewline -Encoding ascii
curl.exe -sS -m 10 http://localhost:8080/ping
curl.exe -sS -m 120 -X POST http://localhost:8080/invocations `
  -H "Content-Type: application/json" `
  --data-binary "@$env:TEMP\hi.json"
```

### Services

| Service | URL |
| --- | --- |
| Agent | http://localhost:8080 |
| OpenSearch | http://localhost:9200 |
| OpenSearch Dashboards | http://localhost:5601 |
| OTLP (HTTP / gRPC) | http://localhost:4318 / 4317 |

Init creates workspace **VendorOps Observability**, data source `vendorops-local`, datasets **Docker logs** (`docker-logs*`, `@timestamp`) and **OTel traces** (`otel-v1-apm-span*`, `endTime`), then prints the workspace URL (`http://localhost:5601/w/<id>`).

If Discover says a time field is missing, init re-writes those datasets after the indices have documents. Hard-refresh the workspace tab after recreate; old `/w/...` ids are invalid.

### Agent Traces

Dashboards **Observability → Agent Traces** queries `attributes.gen_ai.operation.name` on `otel-v1-apm-span-*`. Data Prepper is set to `output_format: otel` and `index_type: trace-analytics-plain-raw` so Strands `gen_ai.*` attributes keep that path (the default OpenSearch flatten turns them into `span.attributes.gen_ai@operation@name`, which Agent Traces ignores).

The collector copies `gen_ai.system` to `gen_ai.provider.name` when the latter is absent. Spans land a few seconds after invoke (`trace_flush_interval: 5`).

Config lives in `dev-scripts/local`.
