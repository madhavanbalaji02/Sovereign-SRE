# Deploying Sovereign SRE to HuggingFace Spaces

## Prerequisites
- HuggingFace account
- Groq API key (free at console.groq.com)
- Git installed locally

## Steps

### 1. Create the Space
1. Go to https://huggingface.co/spaces/new
2. Set **Name**: `sovereign-sre`
3. Set **SDK**: Docker
4. Set **Visibility**: Public (or Private)
5. Click **Create Space**

### 2. Add the GROQ_API_KEY secret
1. Open your Space → **Settings**
2. Scroll to **Variables and secrets**
3. Click **New secret**
4. Name: `GROQ_API_KEY`, Value: your Groq API key
5. Click **Save**

> The key is injected as an environment variable at runtime and never exposed in build logs.

### 3. Clone the Space repo
```bash
git clone https://huggingface.co/spaces/YOUR_USERNAME/sovereign-sre
cd sovereign-sre
```

### 4. Copy project files
From the Sovereign-SRE project root:
```bash
# Copy backend and mcp_server source
cp -r backend/   sovereign-sre/backend/
cp -r mcp_server/ sovereign-sre/mcp_server/

# Use the HF Dockerfile as the root Dockerfile
cp hf_deploy/Dockerfile    sovereign-sre/Dockerfile
cp hf_deploy/supervisord.conf sovereign-sre/supervisord.conf
cp hf_deploy/README.md     sovereign-sre/README.md
```

### 5. Update supervisord path reference
In `sovereign-sre/supervisord.conf`, the path is already relative — no changes needed.
The Dockerfile copies it to `/etc/supervisor/conf.d/sovereign.conf`.

### 6. Push to HF
```bash
cd sovereign-sre
git add .
git commit -m "deploy: Sovereign SRE on HF Spaces"
git push
```

### 7. Watch the build
- Build logs appear in the Space's **Logs** tab
- First build takes ~5–8 min (downloading Python deps + model weights)
- Space goes **Running** when all 3 supervisord processes are healthy

### 8. Test it
```bash
# Health check
curl https://YOUR_USERNAME-sovereign-sre.hf.space/health

# Run a test incident
curl -X POST https://YOUR_USERNAME-sovereign-sre.hf.space/api/agents/run \
  -H "Content-Type: application/json" \
  -d '{
    "logs": [{
      "level": "ERROR",
      "message": "OOMKilled: payments-service exceeded 512Mi memory limit",
      "timestamp": "2026-05-11T10:00:00Z"
    }],
    "auto_approve": false
  }'
```

## Local test before pushing
```bash
# From project root
docker build -f hf_deploy/Dockerfile -t sovereign-sre-hf .
docker run -p 7860:7860 \
  -e GROQ_API_KEY=your_key_here \
  sovereign-sre-hf

# Then open http://localhost:7860
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Build fails on pip install | Check `backend/requirements.txt` has pinned `transformers<5.0` and `sentence-transformers<3.0` |
| `GROQ_API_KEY` not found | Ensure it's added as a **Secret** (not Variable) in Space Settings |
| ChromaDB crash on startup | Normal — it retries. Backend waits 5s via `startsecs=5` |
| Port 7860 not responding | Check supervisord logs: Space Logs tab → filter `backend` |
| Permission denied on `/tmp` | Should not happen — /tmp is world-writable on HF Spaces |
