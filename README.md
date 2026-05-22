# 🛡️ Sovereign-SRE

<div align="center">

![Sovereign-SRE](https://img.shields.io/badge/Sovereign-SRE-00ffff?style=for-the-badge&logo=kubernetes&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-15-black?style=for-the-badge&logo=next.js&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-13%20Services-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white)
[![Dashboard](https://img.shields.io/badge/Dashboard-AWS_Amplify-orange?style=for-the-badge&logo=amazonaws)](https://main.d2qpjzu9cicpu8.amplifyapp.com)
[![Backend](https://img.shields.io/badge/API-EC2_t3.micro-orange?style=for-the-badge&logo=amazonaws)](http://3.149.31.90/health)

**An Autonomous Self-Healing Infrastructure System — Fully on AWS**

*Detect → Diagnose → Fix → Deploy — All Without Human Intervention*

[Dashboard](https://main.d2qpjzu9cicpu8.amplifyapp.com) • [API](http://3.149.31.90/health) • [Architecture](#️-architecture) • [AWS Setup](#-aws-setup) • [Features](#-features)

</div>

---

## 🎯 Overview

**Sovereign-SRE** is a production-grade autonomous SRE (Site Reliability Engineering) system that combines multi-agent AI with 11 AWS services to detect, diagnose, and fix infrastructure incidents automatically — with a human approval gate before any change is applied.

**Core stack:**
- 🧠 **Multi-Agent AI** — LangGraph state machine + CrewAI (Senior SRE + System Researcher)
- 📚 **Codebase-Aware RAG** — LlamaIndex + RDS pgvector + BGE-M3 embeddings
- ☁️ **Amazon Bedrock** — Claude Haiku for agent reasoning (Groq fallback)
- 🔁 **AWS Step Functions** — durable pipeline orchestration with waitForTaskToken
- 📧 **Amazon SNS** — email approval gate (approve/reject via link)
- 📊 **DynamoDB + S3** — incident history, diffs, and audit trail
- 🚨 **CloudWatch + EventBridge + Lambda** — auto-trigger on real alarms
- 🔧 **MCP Server** — Model Context Protocol for tool execution
- 🖥️ **Next.js Cyberpunk Dashboard** — real-time WebSocket streaming

---

## 🏗️ Architecture

### Full System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SOVEREIGN-SRE — AWS EDITION                          │
├──────────────────────────────┬──────────────────────────────────────────────┤
│        TRIGGER LAYER         │              DATA LAYER                       │
│                              │                                               │
│  CloudWatch Alarm            │  ┌─────────────┐  ┌──────────┐  ┌─────────┐ │
│       │                      │  │  DynamoDB   │  │   RDS    │  │   S3    │ │
│       ▼                      │  │  Incidents  │  │pgvector  │  │Artifacts│ │
│  EventBridge Rule            │  │  + State    │  │  (RAG)   │  │  Diffs  │ │
│       │                      │  └─────────────┘  └──────────┘  └─────────┘ │
│       ▼                      │         ▲                ▲            ▲       │
│  Lambda Trigger              │         │                │            │       │
│       │                      ├─────────┼────────────────┼────────────┼───────┤
│       ▼                      │         │       AGENT PIPELINE        │       │
│  Step Functions ─────────────┼─────────┤                             │       │
│  (waitForTaskToken)          │  ┌──────┴──────────────────────────────────┐  │
│       │                      │  │           FastAPI Backend               │  │
│       ▼                      │  │  ┌──────────────────────────────────┐   │  │
│  SNS Email ──────────────►   │  │  │      LangGraph State Machine     │   │  │
│  Approve / Reject link       │  │  │                                  │   │  │
│       │                      │  │  │  LogMonitor → RootCause → Fixer  │   │  │
│       ▼                      │  │  │       │          │         │     │   │  │
│  /api/approvals/{id}         │  │  │  CloudWatch   CrewAI    Bedrock  │   │  │
│                              │  │  │  Logs (src)  SRE+RAG   Haiku    │   │  │
├──────────────────────────────┤  │  │                                  │   │  │
│       SECRETS LAYER          │  │  │  ← CW Metrics pushed each node  │   │  │
│                              │  │  │  ← DynamoDB saved on complete   │   │  │
│  SSM Parameter Store         │  │  │  ← S3 diff + report stored      │   │  │
│  ├── groq-api-key            │  │  └──────────────────────────────────┘   │  │
│  ├── anthropic-api-key       │  └────────────────────┬────────────────────┘  │
│  ├── github-token            │                       │                        │
│  ├── rds-connection-string   │                       ▼                        │
│  └── sns-topic-arn           │  ┌────────────────────────────────────────┐   │
│   (loaded at startup)        │  │     Next.js Dashboard (Cyberpunk UI)   │   │
│                              │  │  Agent Pipeline · Thoughts · Logs · WS │   │
└──────────────────────────────┴──┴────────────────────────────────────────┴───┘
```

### Event Flow: Alarm → Fix → Approval → Resolved

```
1. CloudWatch detects anomaly (e.g. ErrorRate > 5 in 2 min)
         │
         ▼
2. EventBridge routes alarm state change → Lambda
         │
         ▼
3. Lambda starts Step Functions execution + notifies FastAPI (WebSocket)
         │
         ▼
4. LangGraph pipeline runs:
   LogMonitor (CloudWatch Logs) → RootCauseAnalyst (CrewAI + pgvector RAG)
         → CodeFixer (Bedrock Claude Haiku) → Validator
         │
         ▼
5. Step Functions pauses at waitForTaskToken → SNS sends approval email
         │
         ▼
6. Engineer clicks Approve link in email → /api/approvals/{id}?action=approve
         │
         ▼
7. Step Functions resumes → fix applied → incident saved to DynamoDB
   diff/report stored in S3 · CW metrics pushed · GitHub PR created
```

### AWS Services Map

| Layer | Service | Role |
|---|---|---|
| Trigger | CloudWatch Alarms | Detect metric breaches (ErrorRate, FailureRate) |
| Trigger | EventBridge | Route alarm state changes to Lambda |
| Trigger | Lambda | Parse alarm, start Step Functions + notify backend |
| Orchestration | Step Functions | Durable pipeline with `waitForTaskToken` approval gate |
| AI | Amazon Bedrock | Claude Haiku for RCA + patch generation |
| AI | Groq (fallback) | Llama 3.3 when Bedrock is unavailable |
| RAG | RDS pgvector | Production vector DB for codebase embeddings |
| Approval | SNS | Email approve/reject links to engineer |
| Logs | CloudWatch Logs | Real-time log source for LogMonitor node |
| Persistence | DynamoDB | Incident history + agent state (90-day TTL) |
| Artifacts | S3 | Diffs, reports, log snapshots (30-day lifecycle) |
| Secrets | SSM Parameter Store | API keys loaded into env at startup |
| IAM | IAM Role | `sovereign-sre-execution-role` (least-privilege) |

---

## ✨ Features

### 🚨 Auto-Triggered Healing
- CloudWatch Alarms detect real infrastructure anomalies
- EventBridge routes alarm state changes to a Lambda function
- Lambda starts the full pipeline automatically — zero manual intervention

### 🔍 Intelligent Log Monitoring
- Pulls from CloudWatch Logs in real-time (< 60s lag)
- Severity classification: ERROR / CRITICAL → triggers pipeline
- Falls back to logs passed directly to the API for manual triggers

### 🧠 AI-Powered Root Cause Analysis
- **CrewAI Multi-Agent System**:
  - 👨‍💻 **Senior SRE Agent** — diagnoses issues with 10+ years of simulated experience
  - 🔬 **System Researcher Agent** — queries pgvector RAG for relevant code patterns
- Amazon Bedrock (Claude Haiku) for reasoning; Groq (Llama 3.3) as fallback
- Confidence scoring for every proposed diagnosis

### 📚 Codebase-Aware RAG
- **LlamaIndex** pipeline with **BGE-M3** embeddings (local HuggingFace)
- **RDS pgvector** for production vector storage (replaces ChromaDB)
- Language-aware code chunking (Python, TypeScript, Go, and more)
- Migrate existing ChromaDB index: `python aws/pgvector/migrate.py`

### 🔧 Autonomous Code Fixing
- Bedrock Claude Haiku generates targeted patches
- Diff preview stored in S3 with presigned URL
- **Human-in-the-Loop approval gate**: engineer gets email, clicks Approve/Reject

### 📧 Email Approval Gate (SNS + Step Functions)
- Step Functions pauses execution with `waitForTaskToken`
- SNS sends an email with the proposed diff and two links
- Clicking Approve resumes the pipeline; Reject marks incident unresolved
- Approval expires in 1 hour automatically

### 📊 Full Incident Audit Trail
- Every incident saved to DynamoDB (status, confidence, cost, resolution time)
- Diffs, reports, and log snapshots stored in S3
- Custom CloudWatch metrics: `PipelineStart`, `FixApplied`, `BedrockCostUSD`
- Query via `GET /api/incidents` and `GET /api/metrics/summary`

### 🚀 GitHub Integration
- Automatic branch creation and commit generation
- Pull request submission with detailed descriptions

### 🖥️ Cyberpunk Dashboard
- Real-time WebSocket streaming of agent thoughts
- Visual pipeline: Log Monitor → Root Cause → Code Fixer → Approval → Validator
- Terminal-style log viewer with filtering

---

## 🚀 Live Deployment

| Component | AWS Service | URL / Endpoint |
|---|---|---|
| Next.js Dashboard | AWS Amplify | https://main.d2qpjzu9cicpu8.amplifyapp.com |
| FastAPI Backend | EC2 t3.micro | http://3.149.31.90 |
| Vector DB | RDS pgvector | sovereign-sre-db.creky0ag2sa8.us-east-2.rds.amazonaws.com |
| Incident Store | DynamoDB | sovereign-sre-incidents |
| Artifact Store | S3 | sovereign-sre-artifacts-574772738370 |
| AI Inference | Bedrock | us.anthropic.claude-haiku-4-5-20251001-v1:0 |
| Pipeline Orch. | Step Functions | sovereign-sre-pipeline |
| Alerts | CloudWatch | 8 custom metrics, 3 alarms |
| Trigger | EventBridge | sovereign-sre-alarm-trigger |
| Remediation | Lambda | sovereign-sre-remediation-trigger |
| Approvals | SNS | sovereign-sre-approvals |
| Secrets | SSM | /sovereign-sre/* (7 parameters) |
| CI/CD | GitHub Actions | `.github/workflows/deploy.yml` |

### Cost Table — 13 AWS Services

| Service | Free Tier | Monthly Cost |
|---|---|---|
| EC2 t3.micro | 750 hrs/month (12 months) | $0 |
| AWS Amplify | 1,000 build min + 15 GB | $0 |
| RDS db.t3.micro | 750 hrs/month (12 months) | $0 |
| DynamoDB | 25 GB + 25 RCU/WCU forever | $0 |
| S3 | 5 GB free | $0 |
| Lambda | 1M requests free | $0 |
| Step Functions | 4K state transitions free | $0 |
| CloudWatch | 10 alarms + 5 GB logs | $0 |
| SNS | 1M email notifications | $0 |
| SSM Parameter Store | Standard params free | $0 |
| EventBridge | 1M events free | $0 |
| Bedrock Claude Haiku | No free tier | ~$1 |
| Elastic IP | Free while EC2 running | $0 |
| **TOTAL** | | **~$1/month** |

> **Cost guardrail:** Always **terminate** (not stop) EC2 — stopped instances still charge Elastic IP at $0.005/hr.

---

## ☁️ AWS Setup

### Prerequisites

- AWS account with programmatic access (IAM user with admin or scoped permissions)
- Python 3.11+, `pip install boto3 rich python-dotenv`

### 1. Configure credentials

```bash
cp .env.example .env
# Fill in: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION,
#          AWS_ACCOUNT_ID, GROQ_API_KEY, SNS_APPROVAL_EMAIL
```

### 2. Create all AWS resources

```bash
python3 aws/setup.py
```

Creates in order (all idempotent — safe to re-run):
IAM role → S3 → DynamoDB → SNS → SSM → CloudWatch → Firehose → RDS → EventBridge → Lambda → Step Functions → EventBridge target

### 3. Confirm your approval email

Check your inbox for an **AWS SNS subscription confirmation** email and click the link. You won't receive approval notifications until confirmed.

### 4. Migrate embeddings to pgvector (once RDS is ready)

```bash
python3 aws/setup.py           # picks up RDS endpoint once provisioned
python3 aws/pgvector/migrate.py
```

### 5. Run tests

```bash
pytest tests/ -v               # 31 pass, 1 skip — all AWS calls mocked with moto
```

### 6. Fire a test incident

```bash
curl -X POST http://localhost:8001/api/pipeline/trigger \
  -H "Content-Type: application/json" \
  -d '{"trigger_source":"manual","alarm_reason":"OOMKilled payments-service 512Mi exceeded","severity":"high"}'
```

### Tear down

```bash
python3 aws/teardown.py
```

### Cost Table

| Service | Free Tier | Est. Monthly Cost |
|---|---|---|
| Bedrock Claude Haiku | No free tier | ~$1 |
| RDS db.t3.micro | 750 hrs/month (12 months) | $0 |
| Step Functions | 4,000 state transitions | $0 |
| DynamoDB | 25 GB + 25 RCU/WCU forever | $0 |
| S3 | 5 GB free | $0 |
| Lambda | 1M requests free | $0 |
| CloudWatch | 10 alarms + 5 GB logs | $0 |
| SNS | 1M email notifications | $0 |
| Kinesis Firehose | 500K records (first month) | $0 |
| SSM Parameter Store | Standard params free | $0 |
| EventBridge | 1M events free | $0 |
| **TOTAL** | | **~$1/month** |

---

## 🚀 Quick Start (Local)

### Prerequisites

- 🐳 Docker Desktop (with Compose v2)
- 🐍 Python 3.11+
- 📦 Node.js 20+

### 1. Clone & configure

```bash
git clone https://github.com/madhavanbalaji02/Sovereign-SRE.git
cd Sovereign-SRE
cp .env.example .env
# Edit .env with your GROQ_API_KEY (minimum required for local dev)
```

### 2. Start infrastructure

```bash
docker compose up -d    # starts ChromaDB, MCP Server, FastAPI backend
```

### 3. Index your codebase

```bash
python3 -m backend.rag.codebase_observer --workspace .
```

### 4. Start the dashboard

```bash
cd frontend && npm install && npm run dev
```

Open http://localhost:3000

### 5. (Optional) Activate AWS integration

```bash
python3 aws/setup.py                  # provision all AWS resources
python3 aws/pgvector/migrate.py       # migrate embeddings to RDS pgvector
```

---

## 📁 Project Structure

```
Sovereign-SRE/
├── aws/                        # AWS integration (11 services)
│   ├── config.py              # Resource names, ARNs, region constants
│   ├── setup.py               # Creates ALL resources (idempotent)
│   ├── teardown.py            # Destroys all resources safely
│   ├── bedrock/               # Claude Haiku LLM client + fallback
│   ├── pgvector/              # RDS pgvector client, retriever, migration
│   ├── step_functions/        # ASL definition, deployer, executor
│   ├── cloudwatch/            # Log source, custom metrics, alarms
│   ├── eventbridge/           # Alarm → Lambda routing rules
│   ├── lambda_functions/      # Remediation trigger handler
│   ├── sns/                   # Email approval gate
│   ├── dynamodb/              # Incident store + agent state
│   ├── s3/                    # Artifact store (diffs, reports, logs)
│   └── ssm/                   # Secrets manager (replaces .env in prod)
├── backend/
│   ├── api/
│   │   ├── main.py            # FastAPI app (SSM load at startup)
│   │   └── routes/
│   │       ├── agents.py      # Pipeline + WebSocket endpoints
│   │       ├── rag.py         # RAG query endpoints
│   │       └── aws_routes.py  # /api/pipeline/trigger, /api/incidents,
│   │                          # /api/approvals/{id}, /api/metrics/summary
│   ├── agents/
│   │   ├── graph.py           # LangGraph state machine (CW + metrics + S3)
│   │   ├── crew.py            # CrewAI — Senior SRE + System Researcher
│   │   ├── state.py           # Shared state schemas
│   │   ├── human_loop.py      # SNS email gate + local fallback
│   │   └── github_tool.py     # Autonomous PR creation
│   └── rag/
│       ├── query_engine.py    # pgvector (prod) / ChromaDB (local) retriever
│       └── codebase_observer.py  # Indexer — writes to pgvector + ChromaDB
├── frontend/                   # Next.js 15 cyberpunk dashboard
├── mcp_server/                 # Model Context Protocol tool server
├── hf_deploy/                  # HuggingFace Spaces single-container deploy
├── tests/
│   ├── test_aws/              # 32 tests — all AWS mocked with moto
│   │   ├── test_bedrock.py
│   │   ├── test_cloudwatch.py
│   │   ├── test_dynamodb.py
│   │   ├── test_s3.py
│   │   ├── test_sns.py
│   │   ├── test_step_functions.py
│   │   ├── test_pgvector.py
│   │   └── test_full_pipeline.py
│   └── stress_test.py
├── docker-compose.yml
├── check_infra.py
└── README.md
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `GROQ_API_KEY` | Groq API key (free at console.groq.com) | — |
| `GROQ_MODEL` | Groq model name | `llama-3.3-70b-versatile` |
| `ANTHROPIC_API_KEY` | Anthropic key (if `LLM_PROVIDER=claude`) | — |
| `AWS_ACCESS_KEY_ID` | AWS access key | — |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | — |
| `AWS_DEFAULT_REGION` | AWS region | `us-east-1` |
| `AWS_ACCOUNT_ID` | 12-digit AWS account ID | — |
| `BEDROCK_ENABLED` | Use Amazon Bedrock for LLM | `true` |
| `BEDROCK_DEFAULT_MODEL` | Bedrock model alias | `haiku` |
| `BEDROCK_FALLBACK_TO_OLLAMA` | Fall back to Groq if Bedrock fails | `true` |
| `USE_PGVECTOR` | Use RDS pgvector instead of ChromaDB | `false` |
| `STATE_MACHINE_ARN` | Step Functions state machine ARN | — |
| `SNS_TOPIC_ARN` | SNS topic ARN for approvals | — |
| `SNS_APPROVAL_EMAIL` | Email to receive approve/reject links | — |
| `DYNAMODB_TABLE` | DynamoDB table name | `sovereign-sre-incidents` |
| `S3_BUCKET` | S3 bucket for artifacts | `sovereign-sre-artifacts-{account}` |
| `GITHUB_TOKEN` | GitHub PAT for PR creation | — |
| `EMBED_MODEL` | HuggingFace embedding model | `BAAI/bge-m3` |
| `HUMAN_APPROVAL_REQUIRED` | Require approval before fixing | `true` |

---

## 🤖 LLM Providers

Sovereign-SRE supports three LLM backends, switchable via env vars:

```bash
# Amazon Bedrock — Claude Haiku (default for AWS deployments)
BEDROCK_ENABLED=true
BEDROCK_DEFAULT_MODEL=haiku         # $0.00025/1K input tokens
# BEDROCK_DEFAULT_MODEL=sonnet      # used for final code-fix generation

# Groq — Llama 3.3 on LPU hardware (free tier, used as fallback)
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile

# Anthropic Claude (highest reasoning quality)
LLM_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-sonnet-4-6
```

Embeddings always run **locally** via HuggingFace (`BAAI/bge-m3`) — no API key needed.

---

## 🎓 Technical Highlights

This project demonstrates production-level proficiency across the full engineering stack:

| Domain | Technologies |
|---|---|
| **Cloud Architecture** | AWS (11 services), IAM least-privilege, event-driven design |
| **AI/ML Engineering** | RAG pipelines, vector embeddings, multi-agent systems, LLMs |
| **Backend** | FastAPI, async Python, WebSockets, LangGraph, CrewAI |
| **Databases** | PostgreSQL + pgvector, DynamoDB, S3, ChromaDB |
| **DevOps/SRE** | Incident response automation, CloudWatch observability, IaC |
| **Frontend** | Next.js 15, React 19, real-time streaming UI |
| **Testing** | pytest, moto (AWS mocking), 31 passing tests |

---

## 🤗 HuggingFace Spaces Demo

Run Sovereign-SRE as a public demo at zero server cost. Uses a single Docker container with supervisord managing ChromaDB, MCP server, and FastAPI.

**Live demo:** https://madhavan02-sovereign-sre.hf.space

```bash
# Quick deploy to HF Spaces
git clone https://huggingface.co/spaces/YOUR_USERNAME/sovereign-sre
cp -r backend/ mcp_server/ sovereign-sre/
cp hf_deploy/Dockerfile hf_deploy/supervisord.conf hf_deploy/README.md sovereign-sre/
cd sovereign-sre && git add . && git commit -m "deploy" && git push
```

See [`hf_deploy/DEPLOY_STEPS.md`](hf_deploy/DEPLOY_STEPS.md) for the full guide.

---

## 📜 License

MIT License — feel free to use this for your own SRE adventures.

---

<div align="center">

**Built with 🤖 by the future of autonomous infrastructure**

*"The best SRE is the one who automates themselves out of a job."*

</div>
