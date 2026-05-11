---
title: Sovereign SRE
emoji: 🛡️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# 🛡️ Sovereign SRE

Autonomous self-healing infrastructure agent powered by **Groq** (Llama 3.3 on LPU hardware).

Detects anomalies → performs root-cause analysis → generates patches → submits for human approval.

## How to use

Open the Space URL in your browser and paste an incident description into the form.

Or call the API directly:

```bash
curl -X POST https://madhavan02-sovereign-sre.hf.space/api/agents/run \
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

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Demo UI |
| `/api/agents/run` | POST | Run SRE pipeline |
| `/api/agents/approve` | POST | Approve/reject a fix |
| `/api/agents/pending` | GET | List pending approvals |
| `/api/rag/query` | POST | Query codebase RAG |
| `/health` | GET | Health check |
| `/docs` | GET | Interactive API docs |

## Configuration

Requires `GROQ_API_KEY` set as a Space secret:  
**Settings → Variables and secrets → New secret → `GROQ_API_KEY`**

Get a free key at [console.groq.com](https://console.groq.com).

## Architecture

```
Port 7860 (public)
    └── FastAPI backend (Sovereign SRE)
            ├── localhost:8000 → ChromaDB (in-memory, resets on restart)
            └── localhost:8081 → MCP Server (tool execution)
```

All 3 services run in a single container managed by supervisord.
