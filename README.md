# 🛡️ Sovereign-SRE

<div align="center">

![Sovereign-SRE](https://img.shields.io/badge/Sovereign-SRE-00ffff?style=for-the-badge&logo=kubernetes&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-15-black?style=for-the-badge&logo=next.js&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)

**An Autonomous Self-Healing Infrastructure System**

*Detect → Diagnose → Fix → Deploy — All Without Human Intervention*

[Demo](#demo) • [Architecture](#architecture) • [Quick Start](#quick-start) • [Features](#features)

</div>

---

## 🎯 Overview

**Sovereign-SRE** is a production-grade autonomous SRE (Site Reliability Engineering) system that combines the power of:

- 🧠 **Multi-Agent AI** (LangGraph + CrewAI)
- 📚 **Codebase-Aware RAG** (LlamaIndex + ChromaDB)
- 🤖 **Local LLMs** (Ollama with Llama 3.3)
- 🔧 **Model Context Protocol** (MCP) for tool execution
- ⚡ **Human-in-the-Loop Approval Gates**

The result? A system that automatically detects infrastructure issues, analyzes root causes using AI agents that understand your codebase, generates fixes, and submits pull requests — all while keeping humans in control of critical decisions.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           SOVEREIGN-SRE                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐            │
│  │   Ollama     │     │   ChromaDB   │     │  MCP Server  │            │
│  │ Llama 3.3    │     │Vector Store  │     │   Tools      │            │
│  │   BGE-M3     │     │              │     │              │            │
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
- **LlamaIndex** pipeline with **BGE-M3** embeddings
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
# Start all services (Ollama, ChromaDB, MCP Server, Backend)
docker-compose up -d

# Wait for Ollama to pull models (first run takes ~5-10 min)
docker-compose logs -f ollama-loader
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
┌─────────────┬──────────┬───────────────────┐
│ Service     │ Status   │ Details           │
├─────────────┼──────────┼───────────────────┤
│ Ollama      │ ✅ Active │ 2 model(s)        │
│ ChromaDB    │ ✅ Active │ 0 collection(s)   │
│ MCP Server  │ ✅ Active │ 2 tool(s)         │
│ Backend     │ ✅ Active │ healthy           │
└─────────────┴──────────┴───────────────────┘
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
| `GEMINI_API_KEY` | Google Gemini API key | - |
| `ANTHROPIC_API_KEY` | Anthropic Claude API key | - |
| `GITHUB_TOKEN` | GitHub PAT for PR creation | - |
| `OLLAMA_HOST` | Ollama API URL | `http://ollama:11434` |
| `CHROMA_HOST` | ChromaDB URL | `http://chromadb:8000` |
| `OLLAMA_LLM_MODEL` | LLM model name | `llama3.3` |
| `OLLAMA_EMBED_MODEL` | Embedding model | `bge-m3` |

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
