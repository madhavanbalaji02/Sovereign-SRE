-- pgvector schema for Sovereign-SRE codebase embeddings
-- Run once after RDS instance is created (aws/setup.py executes this)

-- RDS COST: db.t3.micro = FREE TIER (750 hrs/month for 12 months)
-- After free tier: ~$13/month. pgvector index for ~100K chunks uses <1GB.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS code_embeddings (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_path   TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    language    TEXT,
    content     TEXT NOT NULL,
    embedding   vector(1024),  -- BGE-M3 produces 1024-dim embeddings
    metadata    JSONB,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(file_path, chunk_index)
);

CREATE INDEX IF NOT EXISTS code_embeddings_ivfflat
    ON code_embeddings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE TABLE IF NOT EXISTS incident_embeddings (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id  TEXT NOT NULL,
    content      TEXT NOT NULL,
    embedding    vector(1024),
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS incident_embeddings_idx
    ON incident_embeddings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 10);
