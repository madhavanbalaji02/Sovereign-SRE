FROM python:3.11-slim

# System deps + supervisord + chromadb CLI
RUN apt-get update && apt-get install -y \
    supervisor curl git build-essential \
    && rm -rf /var/lib/apt/lists/*

# HF Spaces requires non-root user with UID 1000
RUN useradd -m -u 1000 hfuser

WORKDIR /app

# Install backend Python deps (heavy — do first for cache)
COPY backend/requirements.txt /tmp/backend-requirements.txt
RUN pip install --no-cache-dir -r /tmp/backend-requirements.txt

# Install mcp_server Python deps
COPY mcp_server/requirements.txt /tmp/mcp-requirements.txt
RUN pip install --no-cache-dir -r /tmp/mcp-requirements.txt

# Install chromadb CLI (for `chroma run` command)
RUN pip install --no-cache-dir "chromadb[cli]"

# Copy application code
COPY backend/ /app/backend/
COPY mcp_server/ /app/mcp_server/

# Copy supervisord config
COPY hf_deploy/supervisord.conf /etc/supervisor/conf.d/sovereign.conf

# Ensure /app is owned by hfuser
RUN chown -R hfuser:hfuser /app

# Redirect all writable paths to /tmp (only writable dir on HF Spaces)
ENV HF_HOME=/tmp/huggingface
ENV TRANSFORMERS_CACHE=/tmp/transformers
ENV SENTENCE_TRANSFORMERS_HOME=/tmp/sentence_transformers
ENV CHROMA_DB_PATH=/tmp/chroma
# Internal service URLs (services talk to each other via localhost)
ENV CHROMA_HOST=http://localhost:8000
ENV MCP_SERVER_HOST=http://localhost:8080
# ChromaDB embedded mode for RAG modules (demo — resets on restart)
ENV CHROMA_MODE=ephemeral

# HF Spaces exposes only port 7860
EXPOSE 7860

USER 1000

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/sovereign.conf"]
