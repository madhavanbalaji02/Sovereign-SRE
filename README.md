# 🛡️ Sovereign-SRE

<div align="center">

![Sovereign-SRE](https://img.shields.io/badge/Sovereign-SRE-00ffff?style=for-the-badge&logo=kubernetes&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-15-black?style=for-the-badge&logo=next.js&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)
[![HuggingFace Spaces](https://img.shields.io/badge/🤗%20HuggingFace-Spaces-orange?style=for-the-badge)](https://madhavan02-sovereign-sre.hf.space)

**An Autonomous Self-Healing Infrastructure System**

*Detect → Diagnose → Fix → Deploy — All Without Human Intervention*

[Live Demo](https://madhavan02-sovereign-sre.hf.space) • [Architecture](#architecture) • [Quick Start](#quick-start) • [Features](#features) • [Deploy to HF Spaces](#deploy-to-huggingface-spaces)

</div>

---

## 🎯 Overview

**Sovereign-SRE** is a production-grade autonomous SRE (Site Reliability Engineering) system that combines the power of:

- 🧠 **Multi-Agent AI** (LangGraph + CrewAI)
- 📚 **Codebase-Aware RAG** (LlamaIndex + ChromaDB)
- ⚡ **Cloud LLMs** (Groq — Llama 3.3 on LPU hardware, free tier available)
- 🔧 **Model Context Protocol** (MCP) for tool execution
- 🛑 **Human-in-the-Loop Approval Gates**

The result? A system that automatically detects infrastructure issues, analyzes root causes using AI agents that understand your codebase, generates fixes, and submits pull requests — all while keeping humans in control of critical decisions.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           SOVEREIGN-SRE                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐            │
│  │  Groq API   │     │   ChromaDB   │     │  MCP Server  │            │
│  │ Llama 3.3   │     │Vector Store  │     │   Tools      │            │
│  │  BGE-M3 emb  │     │              │     │              │            │
│  └──────┬───────┘     └──────┬───────┘     └──────┬───────┘            │
│         │                    │                    │                     │
│         └────────────────────┼────────────────────┘                     │
│                              │                                          │
│  ┌───────────────────────────┴───────────────────────────────┐         │
│  │                    Backend (FastAPI)                       │         │
│  │  ┌─────────────────────────────────────────────────────┐  │         │
│  │  │               LangGraph State Machine                │  │         │
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────┐ │  │         │
│  │  │  │   Log    │→ │Root Cause│→ │  Code    │→ │Valid│ │  │         │
│  │  │  │ Monitor  │  │ Analyst  │  │  Fixer   │  │ator │ │  │         │
│  │  │  └──────────┘  └────┬─────┘  └────┬─────┘  └─────┘ │  │         │
│  │  │                     │             │                 │  │         │
│  │  │              ┌──────┴──────┐     ┌┴┐               │  │         │
│  │  │              │  CrewAI     │     │👤│ Human        │  │         │
│  │  │              │ SRE + RAG   │     │  │ Approval     │  │         │
│  │  │              └─────────────┘     └──┘               │  │         │
│  │  └─────────────────────────────────────────────────────┘  │         │
│  └───────────────────────────────────────────────────────────┘         │
│                              │                                          │
│                              ▼                                          │
│  ┌───────────────────────────────────────────────────────────┐         │
│  │              Next.js Dashboard (Cyberpunk UI)              │         │
│  │   [Agent Pipeline] [Thought Stream] [Status] [Logs]       │         │
│  └───────────────────────────────────────────────────────────┘         │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

### 🔍 Intelligent Log Monitoring
- Real-time log analysis for anomalies and errors
- Pattern recognition for known failure modes
- Severity classification and prioritization

### 🧠 AI-Powered Root Cause Analysis
- **CrewAI Multi-Agent System**:
  - 👨‍💻 **Senior SRE Agent**: Diagnoses issues with 10+ years of simulated experience
  - 🔬 **System Researcher Agent**: Queries the codebase RAG for relevant implementations
- Confidence scoring for proposed diagnoses

### 📚 Codebase-Aware RAG
- **LlamaIndex** pipeline with **BGE-M3** embeddings (local, via HuggingFace)
- Language-aware code chunking (Python, TypeScript, Go, etc.)
- ChromaDB vector storage for semantic search
- Query your entire codebase: *"How is error handling implemented in the API?"*

### 🔧 Autonomous Code Fixing
- AI-generated patches based on root cause analysis
- Diff generation and preview
- **Human-in-the-Loop approval gates** for safety

### 🚀 GitHub Integration
- Automatic branch creation
- Commit generation with proper messages
- Pull request submission with detailed descriptions
- Labels and metadata for tracking

### 🖥️ Cyberpunk Dashboard
- Real-time WebSocket streaming
- Visual agent pipeline (Decision Tree)
- Live "Thought Stream" from AI agents
- Terminal-style log viewer with filtering

---

## 🚀 Quick Start

### Prerequisites

- 🐳 Docker Desktop (with Compose v2)
- 🐍 Python 3.11+
- 📦 Node.js 20+

### 1. Clone & Setup

```bash
git clone https://github.com/your-username/Sovereign-SRE.git
cd Sovereign-SRE

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env
```

### 2. Start Infrastructure

```bash
# Start all services (ChromaDB, MCP Server, Backend)
docker-compose up -d
```

### 3. Verify Infrastructure

```bash
# Install verification dependencies
pip install httpx rich

# Run infrastructure check
python check_infra.py --local
```

Expected output:
```
✅ All systems operational!
┌────────────────┬──────────┬──────────────────────────┐
│ Service        │ Status   │ Details                  │
├────────────────┼──────────┼──────────────────────────┤
│ Groq API       │ ✅ Active │ Key set (ends ...xxxx)   │
│ ChromaDB       │ ✅ Active │ 0 collection(s)          │
│ MCP Server     │ ✅ Active │ 2 tool(s)                │
│ Backend        │ ✅ Active │ healthy                  │
└────────────────┴──────────┴──────────────────────────┘
```

### 4. Index Your Codebase

```bash
# Index the codebase for RAG
python -m backend.rag.codebase_observer --workspace .
```

### 5. Start the Dashboard

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 to see the Cyberpunk dashboard!

---

## 🧪 Running the Stress Test

Test the complete autonomous healing loop:

```bash
# Dry run (shows what would happen)
python tests/stress_test.py --dry-run

# Full end-to-end test
python tests/stress_test.py --run-e2e
```

The stress test will:
1. 🐛 Inject a bug into the backend
2. 💥 Trigger the bug via API call
3. 🤖 Run the SRE pipeline to detect and diagnose
4. 🔧 Generate a fix
5. ✅ Create a pull request
6. 🧹 Clean up test artifacts

---

## 📁 Project Structure

```
Sovereign-SRE/
├── backend/
│   ├── api/                    # FastAPI application
│   │   ├── main.py            # App entry point
│   │   └── routes/            # API endpoints
│   ├── agents/                 # AI agent system
│   │   ├── graph.py           # LangGraph state machine
│   │   ├── crew.py            # CrewAI configuration
│   │   ├── state.py           # State schemas
│   │   ├── human_loop.py      # Approval manager
│   │   └── github_tool.py     # PR creation
│   └── rag/                    # Codebase RAG
│       ├── codebase_observer.py
│       └── query_engine.py
├── frontend/                   # Next.js dashboard
│   ├── app/                   # App Router pages
│   └── components/            # React components
├── mcp_server/                 # MCP tool server
│   ├── main.py
│   └── tools/
├── hf_deploy/                  # HuggingFace Spaces deployment
│   ├── Dockerfile             # Single-container build (supervisord)
│   ├── supervisord.conf       # Process manager config
│   ├── README.md              # HF Spaces YAML header + docs
│   └── DEPLOY_STEPS.md        # Step-by-step deploy guide
├── tests/
│   └── stress_test.py         # Production stress test
├── docker-compose.yml
├── check_infra.py
└── README.md
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_PROVIDER` | Active LLM backend (`groq`, `grok`, or `claude`) | `groq` |
| `GROQ_API_KEY` | Groq API key — get one free at console.groq.com | - |
| `GROQ_MODEL` | Groq model name | `llama-3.3-70b-versatile` |
| `ANTHROPIC_API_KEY` | Anthropic Claude API key (if `LLM_PROVIDER=claude`) | - |
| `CLAUDE_MODEL` | Claude model name | `claude-sonnet-4-6` |
| `GITHUB_TOKEN` | GitHub PAT for PR creation | - |
| `CHROMA_HOST` | ChromaDB URL | `http://chromadb:8000` |
| `EMBED_MODEL` | HuggingFace embedding model | `BAAI/bge-m3` |

---

## 🤖 LLM Providers

Sovereign-SRE supports multiple LLM backends, switchable via a single env variable:

```bash
# Groq (default — Llama 3.3 on LPU hardware, free tier available)
LLM_PROVIDER=groq
GROQ_MODEL=llama-3.3-70b-versatile   # best quality for RCA + patch gen
# GROQ_MODEL=llama-3.1-8b-instant    # fastest / cheapest for classification
# GROQ_MODEL=mixtral-8x7b-32768      # long context (32K window)
GROQ_API_KEY=your_key_here           # get free at https://console.groq.com

# xAI Grok (alternative cloud option)
LLM_PROVIDER=grok
XAI_API_KEY=your_key_here            # get at https://console.x.ai

# Anthropic Claude (best reasoning quality)
LLM_PROVIDER=claude
CLAUDE_MODEL=claude-sonnet-4-6
ANTHROPIC_API_KEY=your_key_here
```

Embeddings always run **locally** via HuggingFace (`BAAI/bge-m3`) — no embedding API key needed.

### Getting Started

1. Get a free Groq API key at [console.groq.com](https://console.groq.com)
2. Copy `.env.example` to `.env` and set `GROQ_API_KEY`
3. `docker compose up --build`
4. Visit http://localhost:3000

---

## ☁️ AWS Architecture

Sovereign-SRE integrates 11 AWS services for production-grade, cloud-native operation.

### Service Map

```
Trigger layer:
  CloudWatch Alarm → EventBridge → Lambda → Step Functions

AI layer:
  Step Functions → Amazon Bedrock (Claude Haiku) → Agent pipeline

Data layer:
  RDS pgvector (RAG embeddings) + DynamoDB (incidents) + S3 (diffs/reports)

Log streaming:
  Kinesis Firehose → S3 → Agent LogMonitor node

Human approval:
  Step Functions waitForTaskToken → SNS email → /api/approvals/{id}

Secrets:
  SSM Parameter Store → loaded into env at FastAPI startup

IAM:
  sovereign-sre-execution-role (least-privilege inline policy)
```

### Quick AWS Setup

```bash
# 1. Configure AWS credentials
aws configure

# 2. Create all resources (idempotent — safe to re-run)
python aws/setup.py

# 3. Migrate existing ChromaDB embeddings to pgvector
python aws/pgvector/migrate.py

# 4. Run tests (all AWS calls mocked with moto)
pytest tests/ -v

# 5. Fire a test incident end-to-end
curl -X POST http://localhost:8001/api/pipeline/trigger \
  -H "Content-Type: application/json" \
  -d '{"trigger_source":"manual","alarm_reason":"OOMKilled payments-service","severity":"high"}'

# Tear down all resources when done
python aws/teardown.py
```

### AWS Cost Table

All services are within free tier or near-zero cost for portfolio/demo use:

| Service          | Free Tier                  | Est. Monthly Cost |
|------------------|----------------------------|-------------------|
| Bedrock (Haiku)  | No free tier               | ~$1               |
| RDS db.t3.micro  | 750 hrs free (12 months)   | $0                |
| Step Functions   | 4K state transitions free  | $0                |
| DynamoDB         | 25 GB + 25 RCU/WCU forever | $0                |
| S3               | 5 GB free                  | $0                |
| Lambda           | 1M requests free           | $0                |
| CloudWatch       | 10 alarms + 5 GB logs free | $0                |
| SNS              | 1M email notifs free       | $0                |
| Kinesis Firehose | 500K records free          | $0                |
| SSM Param Store  | Standard params free       | $0                |
| EventBridge      | 1M events free             | $0                |
| **TOTAL**        |                            | **~$1/month**     |

> **Cost guardrail:** `NEVER ADD` SageMaker endpoints, EC2, ECS, or Redshift — those cost real money.

### AWS Directory Structure

```
aws/
├── config.py                  # Resource names, ARNs, region constants
├── setup.py                   # Creates ALL resources (idempotent)
├── teardown.py                # Destroys all resources safely
├── bedrock/                   # LLM backend (Claude Haiku default)
├── pgvector/                  # Production vector DB (RDS pgvector)
├── step_functions/            # Durable pipeline orchestration
├── kinesis/                   # Real-time log streaming
├── cloudwatch/                # Log source + custom metrics + alarms
├── eventbridge/               # Alarm → Lambda routing rules
├── lambda_functions/          # Remediation trigger Lambda
├── sns/                       # Email approval gate
├── dynamodb/                  # Incident history + agent state
├── s3/                        # Diffs, reports, audit trail
└── ssm/                       # Secure secrets management
```

---

## 🤗 Deploy to HuggingFace Spaces

Run Sovereign-SRE as a public demo with zero server costs. The `hf_deploy/` folder contains a single-container setup managed by **supervisord** — ChromaDB, the MCP server, and the FastAPI backend all run on port 7860.

**Live demo:** https://madhavan02-sovereign-sre.hf.space

### Quick deploy

```bash
# 1. Create a new Docker Space at huggingface.co/spaces/new
# 2. Add GROQ_API_KEY as a Space secret (Settings → Variables and secrets)

# 3. Clone your Space and copy the project files
git clone https://huggingface.co/spaces/YOUR_USERNAME/sovereign-sre
cp -r backend/ mcp_server/ sovereign-sre/
cp hf_deploy/Dockerfile hf_deploy/supervisord.conf hf_deploy/README.md sovereign-sre/

# 4. Push — first build takes ~5–8 min
cd sovereign-sre && git add . && git commit -m "deploy" && git push
```

See [`hf_deploy/DEPLOY_STEPS.md`](hf_deploy/DEPLOY_STEPS.md) for the full guide.

### HF Spaces architecture

```
Port 7860 (public)
    └── FastAPI backend (Sovereign SRE)
            ├── localhost:8000 → ChromaDB (ephemeral in-memory)
            └── localhost:8081 → MCP Server (tool execution)
```

> ChromaDB runs in ephemeral mode on HF Spaces — vector data resets on container restart.  
> All writable paths are routed to `/tmp` for HF Spaces compatibility.

### Test your deployment

```bash
curl -X POST https://YOUR_USERNAME-sovereign-sre.hf.space/api/agents/run \
  -H "Content-Type: application/json" \
  -d '{
    "logs": [{
      "level": "ERROR",
      "message": "OOMKilled on pod payments-service. Memory limit 512Mi exceeded.",
      "timestamp": "2026-05-11T07:00:00Z"
    }],
    "auto_approve": false
  }'
```

---

## 🎓 Technical Highlights

### For MAANG Interviews

This project demonstrates proficiency in:

- **Distributed Systems**: Docker orchestration, service mesh, health checks
- **AI/ML Engineering**: RAG pipelines, embeddings, multi-agent systems
- **Backend Development**: FastAPI, async Python, WebSockets
- **Frontend Development**: Next.js 15, React 19, real-time streaming
- **DevOps/SRE**: Infrastructure as code, observability, incident response
- **System Design**: Event-driven architecture, state machines, graceful degradation

---

## 📜 License

MIT License - Feel free to use this for your own SRE adventures!

---

<div align="center">

**Built with 🤖 by the future of autonomous infrastructure**

*"The best SRE is the one who automates themselves out of a job."*

</div>
