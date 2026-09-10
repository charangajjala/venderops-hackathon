# VendorOps

An autonomous procurement agent for a supermarket, built on the [Strands Agents SDK](https://strandsagents.com) and deployed on [Amazon Bedrock AgentCore Runtime](https://aws.amazon.com/bedrock/agentcore/). When a SKU's stock runs low, the agent ranks candidate vendors by trust, checks each one's real-time stock, sends an RFQ to the first vendor that can actually fulfill it, parses the vendor's email reply, and either auto-issues a purchase order (trusted vendor, complete quote) or escalates to a human buyer (untrusted vendor, or missing terms) — end to end, with no human in the loop unless the agent chooses to ask for one.

**Live demo dashboard:** https://d2sx4lpclh3j7u.cloudfront.net

## Why this exists

Reordering stock from vendors is repetitive, time-sensitive busywork: check what's low, find who can supply it, request quotes, compare terms, decide whether to trust the reply, place the order, confirm it landed. VendorOps automates the whole loop while keeping a human in the decision seat for exactly the cases that actually need judgment — an unfamiliar vendor's quote, missing terms, nobody able to fulfill the order — instead of either blocking on every step or silently auto-approving everything.

## How it works

Two independent triggers feed the same deployed agent:

### Loop A — stock drops, agent reorders

```
Inventory quantity_on_hand crosses below reorder_threshold (DynamoDB Streams)
  -> Reorder Checker Lambda (idempotent: skips if an RFQ is already open for that SKU)
  -> invokes the AgentCore Runtime
  -> agent: list_candidate_vendors -> check_vendor_stock on each, in trust order,
     until one actually has enough stock -> create_rfq (writes RFQs + OpenRFQs,
     emails the vendor via SES)
```

### Loop B — vendor replies, agent decides

```
Vendor's email reply arrives
  -> SES receipt rule: raw MIME -> S3, notification -> SNS -> SQS
  -> Service Lambda: dedupes on SES message-id, parses the MIME body,
     correlates the RFQ id out of the subject/body
  -> invokes the AgentCore Runtime
  -> agent: get_rfq + get_vendor -> record_quote
       trusted vendor + complete quote  -> create_purchase_order
         (issues the PO, restocks quantity_on_hand by the ordered amount,
          closes the SKU's open-RFQ slot, emails a PO confirmation)
       untrusted vendor / missing terms -> notify_buyer (escalates by email)
  -> Service Lambda sends the agent's reply back over SES
```

An interactive dashboard (React + a small API Gateway/Lambda backend) sits on top for visibility and human decisions: live Inventory/Vendors/RFQs/Purchase Orders views, Approve/Reject actions on any RFQ pending a buyer decision (closing the escalation loop from a click instead of a manual DynamoDB edit), and a "sell"/"restock" control on Inventory that writes straight to the real table — so an adjustment there drives the real Streams → Reorder Checker → AgentCore pipeline, not a mock.

## Architecture

```
                                    ┌─────────────────────┐
   Inventory adjustment ───────────▶  DynamoDB: Inventory │──── Streams ───┐
   (dashboard button, or                                  │                │
    dev-scripts/simulate_sale.py)  └─────────────────────┘                 ▼
                                                              ┌───────────────────────┐
                                                              │ Reorder Checker Lambda │
                                                              │ (skip if OpenRFQs open)│
                                                              └───────────┬────────────┘
                                                                          │ invoke_agent_runtime
                                                                          ▼
   Vendor's reply email                                     ┌───────────────────────────┐
        │                                                    │   Bedrock AgentCore        │
        ▼                                                    │   Runtime (Strands Agent)  │
   SES receipt rule                                          │                             │
        │  raw MIME -> S3 (raw-emails)                       │   tools:                   │
        │  notification -> SNS -> SQS                        │   - get_inventory_status   │
        ▼                                                     │   - list_candidate_vendors │
   Service Lambda ───────── invoke_agent_runtime ───────────▶ │   - check_vendor_stock     │
   (dedupe, MIME parse,                                       │   - create_rfq             │
    RFQ-id correlation,                                       │   - get_rfq / get_vendor   │
    sends reply via SES)  ◀──────────── agent response ────── │   - record_quote           │
                                                                │   - create_purchase_order  │
                                                                │   - notify_buyer           │
                                                                │                             │
                                                                │   session state -> S3       │
                                                                └──────────┬──────────────────┘
                                                                           │ reads/writes
                                                                           ▼
                              DynamoDB: Vendors, VendorStock-<vendor> (one table per
                              vendor), RFQs, OpenRFQs, Quotes, PurchaseOrders, Idempotency

   Dashboard (React, CloudFront + S3) ──── API Gateway HTTP API ──── Dashboard API Lambda
   Inventory / Vendors / RFQs (+ Approve/Reject) / Purchase Orders  (same tables, plain boto3)
```

Everything is serverless — no VPC, no NAT Gateway, no always-on compute. DynamoDB, S3, SNS, SQS, SES, Lambda, and Bedrock are all reachable directly, so idle cost is effectively zero (see [Cost](#cost) below).

## Why the design looks the way it does

- **One DynamoDB table per vendor's stock** (`VendorStock-<vendor>`), instead of one table partitioned by vendor. This lets the demo show two independently-moving "databases" going out of sync — our shelf running low is a separate fact from whether a given vendor's own stock can cover it — and makes the failover path (skip an out-of-stock vendor, try the next one) concrete rather than simulated in-memory.
- **Trust-tiered auto-approval.** A trusted vendor's complete quote auto-issues a PO; anything else (untrusted vendor, missing price/lead-time/MOQ) escalates to a human via `notify_buyer` rather than guessing. The dashboard's Approve/Reject actions close that escalation loop.
- **Atomic duplicate-PO guard.** `create_purchase_order` claims the RFQ's `awarded` status via a DynamoDB conditional update before writing the PO, so a retried invocation (or a race between the dashboard and the agent) can't issue two POs for the same RFQ.
- **SES writes raw email to S3 first, SNS just carries the key.** SNS notifications from SES cap out around 150KB and don't reliably carry attachments; going through S3 avoids that limit entirely.
- **Session persistence via `strands.session.s3_session_manager.S3SessionManager`**, reusing the same S3 bucket the runtime already has - no separate memory service to provision.
- **Self-contained Lambda handlers** (`lambda_functions/*`) never import the `vendorops_agent` package - that would pull in `strands`/`bedrock_agentcore`/`pydantic` transitively through `agent.py`, which a thin DynamoDB-Streams watcher or CRUD API has no use for.

## Repo layout

```
src/vendorops_agent/       Strands agent - tools, system prompt, AgentCore entrypoint
lambda_functions/
  reorder_checker/           DynamoDB Streams -> AgentCore invoke (Loop A trigger)
  service/                   SQS -> AgentCore invoke -> SES reply (Loop B)
  dashboard_api/              REST-ish CRUD + approve/reject over the same tables
frontend/                    React (Vite) dashboard
infra/
  bootstrap/                  shared Terraform state backend
  environments/dev/           root module wiring every other module together
  modules/
    storage/                   S3: raw-emails, agent-sessions
    messaging/                 SES receipt rule, SNS, SQS + DLQ
    dynamodb/                  Inventory, Vendors, VendorStock-*, RFQs, OpenRFQs, Quotes,
                                PurchaseOrders, Idempotency
    agentcore/                  ECR repo + lifecycle policy, AgentCore Runtime, execution role
    compute/                    Reorder Checker + Service Lambdas
    api/                        Dashboard API Lambda + API Gateway HTTP API
    frontend/                   S3 (private) + CloudFront (OAC) for the dashboard
    observability/              SNS alerts, AWS Budget, CloudWatch billing alarms
    dns/                        Cloudflare records for SES domain verification/DKIM/MX
dev-scripts/
  seed_dynamodb.py             Seeds Inventory (below threshold) + Vendors + VendorStock
  simulate_sale.py             Decrements Inventory.quantity_on_hand to trigger Loop A
  push_agent_image.sh          Build + push the agent's container image to ECR
  deploy_frontend.sh           Build the dashboard and sync it to S3 + invalidate CloudFront
```

## Running the agent locally (Docker)

For iterating on the agent's tools/prompt without a full AWS deploy. Requires AWS credentials with access to Bedrock (Nova Micro) and the deployed DynamoDB tables/S3 buckets - this is local *compute*, not a local *backend*.

```bash
export AWS_PROFILE=<your-sso-profile> AWS_REGION=us-east-1
make docker-run-local
```

`docker-compose.yml` mounts your host `~/.aws` read-only and passes `AWS_PROFILE` through, reusing your existing SSO session - no credentials touch a file. If you don't have an SSO profile, copy `.env.example` to `.env` and fill in static IAM-user keys instead (gitignored, but prefer the profile approach when you can).

```bash
curl -sS -m 10 http://localhost:8080/ping
curl -sS -m 120 -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  --data-binary '{"prompt":"Hi"}'
```

Other targets: `make docker-stop-local`, `make docker-stop-local-complete` (also drops volumes), `make docker-logs-local`, `make docker-restart-local`.

A local OpenSearch + Data Prepper + OTel Collector stack comes up alongside the agent for trace inspection (`docker-compose.yml`'s `ENABLE_OTLP_EXPORT: "true"` is local-dev-only - the deployed AgentCore Runtime doesn't export traces there). OpenSearch Dashboards: http://localhost:5601. Config lives in `dev-scripts/local`.

## Deploying to AWS

All infrastructure is Terraform, applied from `infra/environments/dev`:

```bash
export AWS_PROFILE=<your-sso-profile>
export CLOUDFLARE_API_TOKEN=<token with DNS edit on the SES domain's zone>
cd infra/environments/dev
terraform init
terraform apply
```

Then build and push the agent's container image, and deploy the dashboard frontend:

```bash
./dev-scripts/push_agent_image.sh <tag>          # update infra/environments/dev/main.tf's
                                                  # image_tag to the same value, then re-apply
                                                  # module.agentcore so the runtime picks it up
./dev-scripts/deploy_frontend.sh
```

Seed demo data (an Inventory item already below threshold, a mix of trusted/untrusted vendors, and per-vendor stock with one vendor deliberately out of stock so the failover path is reachable on demand):

```bash
python3 dev-scripts/seed_dynamodb.py
```

Then trigger Loop A for real:

```bash
python3 dev-scripts/simulate_sale.py eggs-dozen-freerange 20
```

## Cost

Everything is on-demand/serverless (DynamoDB `PAY_PER_REQUEST`, Lambda, S3, SNS, SQS, API Gateway HTTP API, CloudFront) with an ECR lifecycle policy capping stored agent images at the 5 most recent. At hackathon-demo traffic levels this runs entirely inside AWS's free-tier allowances - actual measured spend via Cost Explorer has stayed at $0.00 (rounding) across the build. A CloudWatch billing alarm + AWS Budget are wired up as a guardrail regardless.

## Observability

CloudWatch Log Groups (explicit retention, not unbounded) for every Lambda and the AgentCore Runtime. CloudWatch Alarms -> SNS -> email for: Lambda error rate, SQS DLQ depth, SQS oldest-message age, and billing thresholds.

## Tech stack

Strands Agents SDK, Amazon Bedrock AgentCore Runtime (native `aws_bedrockagentcore_agent_runtime` Terraform resource), Amazon Bedrock (Nova Micro), DynamoDB, S3, SES, SNS, SQS, Lambda, API Gateway (HTTP API), CloudFront, ECR, CloudWatch, Terraform, React (Vite), Python 3.13 (Lambdas) / 3.11+ (agent), boto3.
