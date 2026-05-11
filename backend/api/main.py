"""
Sovereign-SRE Backend API (Docker Compatible)
==============================================
FastAPI backend for autonomous SRE operations.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import json
import uuid

# =============================================================================
# APP INITIALIZATION
# =============================================================================

app = FastAPI(
    title="Sovereign-SRE Backend",
    description="Backend API for autonomous SRE operations",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# MODELS
# =============================================================================

class RunPipelineRequest(BaseModel):
    logs: list[dict] = Field(..., description="Log entries to analyze")
    run_id: Optional[str] = Field(None, description="Optional run ID")
    auto_approve: bool = Field(False, description="Auto-approve fixes")


class QueryRequest(BaseModel):
    query: str = Field(..., description="Question about the codebase")
    top_k: int = Field(default=5)


# =============================================================================
# STATE
# =============================================================================

demo_state = {
    "status": "idle",
    "current_node": "idle",
    "detected_issues": [],
    "thoughts": [],
}


# =============================================================================
# HEALTH & INFO ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat(), "service": "backend"}


@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse(content="""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sovereign SRE</title>
<style>
  :root { --cyan: #00ffff; --green: #00ff88; --red: #ff4444; --bg: #0a0e1a; --card: #111827; --border: #1f2d40; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: #c9d1d9; font-family: 'Courier New', monospace; min-height: 100vh; padding: 2rem 1rem; }
  h1 { color: var(--cyan); font-size: 2rem; letter-spacing: 2px; text-shadow: 0 0 20px var(--cyan); }
  h1 span { color: #fff; }
  .subtitle { color: #8b949e; margin: .4rem 0 2rem; font-size: .9rem; }
  .badge { display: inline-block; background: #1a2744; border: 1px solid var(--cyan); color: var(--cyan); padding: .2rem .7rem; border-radius: 20px; font-size: .75rem; margin-right: .5rem; }
  .card { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 1.5rem; margin-bottom: 1.5rem; }
  label { display: block; color: #8b949e; font-size: .8rem; margin-bottom: .5rem; text-transform: uppercase; letter-spacing: 1px; }
  textarea { width: 100%; background: #0d1117; border: 1px solid var(--border); border-radius: 6px; color: #e6edf3; font-family: 'Courier New', monospace; font-size: .9rem; padding: .8rem; resize: vertical; min-height: 120px; outline: none; }
  textarea:focus { border-color: var(--cyan); box-shadow: 0 0 8px rgba(0,255,255,.2); }
  select { background: #0d1117; border: 1px solid var(--border); border-radius: 6px; color: #e6edf3; font-family: 'Courier New', monospace; font-size: .9rem; padding: .6rem .8rem; outline: none; }
  .row { display: flex; gap: 1rem; align-items: flex-end; flex-wrap: wrap; }
  button { background: transparent; border: 1px solid var(--cyan); color: var(--cyan); padding: .7rem 1.8rem; border-radius: 6px; font-family: 'Courier New', monospace; font-size: .9rem; cursor: pointer; letter-spacing: 1px; transition: all .2s; }
  button:hover { background: var(--cyan); color: #000; box-shadow: 0 0 15px var(--cyan); }
  button:disabled { opacity: .4; cursor: not-allowed; }
  .pipeline { display: flex; gap: .5rem; flex-wrap: wrap; margin-bottom: 1rem; }
  .step { display: flex; align-items: center; gap: .4rem; background: #0d1117; border: 1px solid var(--border); border-radius: 20px; padding: .3rem .9rem; font-size: .8rem; color: #8b949e; }
  .step.active { border-color: var(--cyan); color: var(--cyan); }
  .step.done { border-color: var(--green); color: var(--green); }
  .step.waiting { border-color: #f9c74f; color: #f9c74f; }
  .thought { border-left: 2px solid var(--border); padding: .5rem 1rem; margin: .5rem 0; font-size: .85rem; }
  .thought .agent { color: var(--cyan); font-size: .75rem; margin-bottom: .2rem; }
  .issue { background: rgba(255,68,68,.1); border: 1px solid var(--red); border-radius: 6px; padding: .6rem 1rem; margin: .4rem 0; font-size: .85rem; color: #ff9999; }
  .status-bar { display: flex; align-items: center; gap: .8rem; padding: .6rem 1rem; border-radius: 6px; font-size: .85rem; margin-bottom: 1rem; }
  .status-bar.running { background: rgba(0,255,255,.08); border: 1px solid var(--cyan); color: var(--cyan); }
  .status-bar.waiting { background: rgba(249,199,79,.08); border: 1px solid #f9c74f; color: #f9c74f; }
  .status-bar.done { background: rgba(0,255,136,.08); border: 1px solid var(--green); color: var(--green); }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: currentColor; animation: pulse 1.2s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.3} }
  #results { display: none; }
  a { color: var(--cyan); text-decoration: none; }
  a:hover { text-decoration: underline; }
  .links { font-size: .8rem; color: #8b949e; }
  .links a { margin-right: 1rem; }
  max-width { max-width: 780px; margin: 0 auto; }
</style>
</head>
<body>
<div style="max-width:780px;margin:0 auto">
  <h1>🛡️ Sovereign <span>SRE</span></h1>
  <p class="subtitle">Autonomous self-healing infrastructure &mdash; Groq &times; Llama 3.3</p>
  <div>
    <span class="badge">LangGraph</span>
    <span class="badge">CrewAI</span>
    <span class="badge">Llama 3.3</span>
    <span class="badge">RAG</span>
  </div>

  <br>

  <div class="card">
    <label>Incident description</label>
    <textarea id="incident" placeholder="OOMKilled on pod payments-service-7d9f in namespace production. Memory limit 512Mi exceeded. Last 3 restarts in 10 min."></textarea>
    <br>
    <div class="row" style="margin-top:.8rem">
      <div>
        <label>Severity</label>
        <select id="severity">
          <option value="high">high</option>
          <option value="medium">medium</option>
          <option value="low">low</option>
        </select>
      </div>
      <button id="submitBtn" onclick="runPipeline()">&#9654; Run SRE Pipeline</button>
    </div>
  </div>

  <div id="results" class="card">
    <div id="statusBar" class="status-bar running"><div class="dot"></div><span id="statusText">Running pipeline…</span></div>

    <div class="pipeline">
      <div class="step" id="step-monitor">📡 Log Monitor</div>
      <div class="step" id="step-rca">🧠 Root Cause</div>
      <div class="step" id="step-fix">🔧 Code Fixer</div>
      <div class="step" id="step-approve">👤 Approval Gate</div>
    </div>

    <div id="issues"></div>

    <label style="margin-top:1rem">Agent thoughts</label>
    <div id="thoughts"></div>
  </div>

  <div class="links">
    <a href="/docs">API docs</a>
    <a href="/health">Health</a>
    <a href="https://github.com/madhavanbalaji02/Sovereign-SRE" target="_blank">GitHub</a>
  </div>
</div>

<script>
const STEPS = {
  log_monitor: 'step-monitor',
  root_cause_analyst: 'step-rca',
  code_fixer: 'step-fix',
  waiting_approval: 'step-approve'
};

async function runPipeline() {
  const incident = document.getElementById('incident').value.trim();
  if (!incident) return;
  const severity = document.getElementById('severity').value;
  const btn = document.getElementById('submitBtn');

  btn.disabled = true;
  document.getElementById('results').style.display = 'block';
  document.getElementById('issues').innerHTML = '';
  document.getElementById('thoughts').innerHTML = '';
  Object.values(STEPS).forEach(id => {
    const el = document.getElementById(id);
    el.classList.remove('active','done','waiting');
  });
  setStatus('running', 'Running pipeline…');

  try {
    const res = await fetch('/api/agents/run', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        logs: [{ level: severity === 'high' ? 'ERROR' : 'WARNING', message: incident, timestamp: new Date().toISOString(), severity }],
        auto_approve: false
      })
    });
    const data = await res.json();

    // Render detected issues
    const issuesEl = document.getElementById('issues');
    if (data.detected_issues && data.detected_issues.length) {
      data.detected_issues.forEach(issue => {
        issuesEl.innerHTML += '<div class="issue">⚠️ ' + escHtml(issue) + '</div>';
      });
    }

    // Render thoughts
    const thoughtsEl = document.getElementById('thoughts');
    (data.messages || []).forEach(m => {
      const stepId = STEPS[m.agent?.toLowerCase().replace(/ /g,'_')] || null;
      thoughtsEl.innerHTML += '<div class="thought"><div class="agent">' + escHtml(m.agent) + '</div>' + escHtml(m.thought) + '</div>';
      if (stepId) document.getElementById(stepId)?.classList.add('done');
    });

    // Set final status
    if (data.status === 'waiting_approval') {
      document.getElementById('step-approve').classList.add('waiting');
      setStatus('waiting', '⏸ Waiting for human approval — POST /api/agents/approve?run_id=' + data.run_id + '&approved=true');
    } else if (data.status === 'completed') {
      setStatus('done', '✅ Pipeline complete');
    } else {
      setStatus('done', 'Status: ' + data.status);
    }

    // Mark current node active
    const activeStep = STEPS[data.current_node];
    if (activeStep && data.status !== 'completed') {
      document.getElementById(activeStep)?.classList.add(data.status === 'waiting_approval' ? 'waiting' : 'active');
    }

  } catch (e) {
    setStatus('done', '❌ Error: ' + e.message);
  } finally {
    btn.disabled = false;
  }
}

function setStatus(type, text) {
  const bar = document.getElementById('statusBar');
  bar.className = 'status-bar ' + type;
  bar.innerHTML = (type === 'running' ? '<div class="dot"></div>' : '') + '<span>' + text + '</span>';
}

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

document.getElementById('incident').addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') runPipeline();
});
</script>
</body>
</html>""")


@app.get("/api/info")
async def info():
    return {
        "name": "Sovereign-SRE Backend",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "rag_query": "/api/rag/query",
            "agents_run": "/api/agents/run",
        }
    }


# =============================================================================
# AGENTS ENDPOINTS
# =============================================================================

@app.post("/api/agents/run")
async def run_pipeline(request: RunPipelineRequest):
    """Run the SRE agent pipeline"""
    run_id = request.run_id or str(uuid.uuid4())
    
    demo_state["status"] = "running"
    demo_state["current_node"] = "log_monitor"
    demo_state["detected_issues"] = []
    demo_state["thoughts"] = []
    
    # Analyze logs
    for log in request.logs:
        if log.get("level", "").upper() in ["ERROR", "CRITICAL"]:
            demo_state["detected_issues"].append(log.get("message", "Unknown error"))
    
    demo_state["thoughts"].append({
        "agent": "LogMonitor",
        "thought": f"Detected {len(demo_state['detected_issues'])} issues",
        "timestamp": datetime.utcnow().isoformat()
    })
    
    if demo_state["detected_issues"]:
        demo_state["current_node"] = "root_cause_analyst"
        demo_state["thoughts"].append({
            "agent": "Senior SRE",
            "thought": "Analyzing root cause of detected errors...",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        demo_state["current_node"] = "code_fixer"
        demo_state["thoughts"].append({
            "agent": "CodeFixer",
            "thought": "Generating fix for identified issue",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        if request.auto_approve:
            demo_state["current_node"] = "validator"
            demo_state["status"] = "completed"
        else:
            demo_state["status"] = "waiting_approval"
    else:
        demo_state["status"] = "completed"
    
    return {
        "run_id": run_id,
        "status": demo_state["status"],
        "current_node": demo_state["current_node"],
        "detected_issues": demo_state["detected_issues"],
        "waiting_approval": demo_state["status"] == "waiting_approval",
        "messages": demo_state["thoughts"]
    }


@app.post("/api/agents/approve")
async def approve_action(run_id: str, approved: bool):
    """Approve or reject a pending fix"""
    if approved:
        demo_state["status"] = "completed"
        demo_state["current_node"] = "validator"
        return {"success": True, "message": "Fix approved"}
    return {"success": True, "message": "Fix rejected"}


@app.get("/api/agents/pending")
async def get_pending():
    """Get pending approvals"""
    if demo_state["status"] == "waiting_approval":
        return {"pending": [demo_state], "count": 1}
    return {"pending": [], "count": 0}


# =============================================================================
# RAG ENDPOINTS
# =============================================================================

@app.post("/api/rag/query")
async def query_codebase(request: QueryRequest):
    """Query the codebase (demo mode - returns mock response)"""
    return {
        "response": f"Response to: '{request.query}'\n\n(Full RAG requires ChromaDB indexing)",
        "sources": [{"file_path": "backend/api/main.py", "language": "python", "score": 0.85}],
        "query": request.query,
        "source_count": 1
    }


@app.post("/api/rag/index")
async def index_codebase():
    """Index the codebase"""
    return {"status": "success", "chunks_indexed": 0, "message": "Indexing not configured in demo mode"}


@app.get("/api/rag/stats")
async def rag_stats():
    """Get RAG stats"""
    return {"collection_name": "sovereign_sre_codebase", "chunk_count": 0, "workspace_path": "/workspace"}


# =============================================================================
# WEBSOCKET
# =============================================================================

@app.websocket("/api/agents/ws/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
