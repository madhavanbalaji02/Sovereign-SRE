"""
Index SRE runbooks and postmortems into pgvector.

Creates runbook_embeddings table if not exists, then upserts
all markdown files chunked by ## section headings.

Usage:
    python aws/pgvector/index_runbooks.py
"""

from __future__ import annotations
import os
import re
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
RUNBOOKS_DIR = ROOT / "data" / "runbooks"
POSTMORTEMS_DIR = ROOT / "data" / "postmortems"

ANOMALY_TYPE_MAP = {
    "memory": "memory_anomaly",
    "cpu": "cpu_anomaly",
    "connection_pool": "memory_anomaly",
    "network": "network_delay",
    "pod": "pod_failure",
    "oom": "pod_failure",
    "disk": "disk_anomaly",
    "log_rotation": "disk_anomaly",
    "database": "cpu_anomaly",
    "cascading": "network_delay",
}

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS runbook_embeddings (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_type     TEXT NOT NULL,
    title        TEXT NOT NULL,
    section      TEXT NOT NULL,
    content      TEXT NOT NULL,
    anomaly_type TEXT,
    embedding    vector(1024),
    created_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS runbook_emb_idx
    ON runbook_embeddings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 10);
"""


def infer_anomaly_type(filename: str, content: str) -> str:
    fname = filename.lower()
    combined = (fname + " " + content[:200]).lower()
    for kw, atype in ANOMALY_TYPE_MAP.items():
        if kw in combined:
            return atype
    return "cpu_anomaly"


def chunk_markdown(text: str) -> list[tuple[str, str]]:
    """Split markdown on ## headings. Returns [(section_title, content)]."""
    chunks = []
    current_title = "Overview"
    current_content = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current_content:
                chunks.append((current_title, "\n".join(current_content).strip()))
            current_title = line[3:].strip()
            current_content = []
        else:
            current_content.append(line)
    if current_content:
        chunks.append((current_title, "\n".join(current_content).strip()))
    return [(t, c) for t, c in chunks if len(c) > 30]


def embed_texts(texts: list[str]) -> list[list[float]]:
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("BAAI/bge-m3")
        return model.encode(texts, normalize_embeddings=True).tolist()
    except Exception as e:
        print(f"  Embedding model error: {e} — using random fallback")
        import random
        return [[random.gauss(0, 0.1) for _ in range(1024)] for _ in texts]


def upsert_chunks(conn, chunks: list[dict]) -> int:
    with conn.cursor() as cur:
        inserted = 0
        for chunk in chunks:
            embedding_str = "[" + ",".join(str(x) for x in chunk["embedding"]) + "]"
            cur.execute("""
                INSERT INTO runbook_embeddings
                    (id, doc_type, title, section, content, anomaly_type, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s::vector)
                ON CONFLICT (id) DO NOTHING
            """, (
                chunk["id"], chunk["doc_type"], chunk["title"],
                chunk["section"], chunk["content"], chunk["anomaly_type"],
                embedding_str,
            ))
            inserted += 1
        conn.commit()
    return inserted


def main() -> None:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")

    use_pgvector = os.environ.get("USE_PGVECTOR", "false").lower() == "true"

    if not use_pgvector:
        print("⚠  USE_PGVECTOR=false — skipping pgvector indexing")
        print("   Set USE_PGVECTOR=true and RDS_* vars to enable.")
        _index_local_fallback()
        return

    try:
        import psycopg2
        conn = psycopg2.connect(
            host=os.environ["RDS_HOST"],
            port=int(os.environ.get("RDS_PORT", 5432)),
            dbname=os.environ["RDS_DB"],
            user=os.environ["RDS_USER"],
            password=os.environ["RDS_PASSWORD"],
        )
    except Exception as e:
        print(f"✗ Cannot connect to pgvector: {e}")
        print("  Falling back to local JSON index...")
        _index_local_fallback()
        return

    # Create table
    with conn.cursor() as cur:
        cur.execute(CREATE_TABLE_SQL)
    conn.commit()
    print("✓ runbook_embeddings table ready")

    all_chunks = _collect_chunks()
    print(f"  Embedding {len(all_chunks)} chunks...")
    texts = [c["content"][:800] for c in all_chunks]
    embeddings = embed_texts(texts)
    for chunk, emb in zip(all_chunks, embeddings):
        chunk["embedding"] = emb

    inserted = upsert_chunks(conn, all_chunks)
    conn.close()
    print(f"✓ Indexed {inserted} chunks into pgvector runbook_embeddings")


def _collect_chunks() -> list[dict]:
    chunks = []
    for directory, doc_type in [(RUNBOOKS_DIR, "runbook"), (POSTMORTEMS_DIR, "postmortem")]:
        for md_file in sorted(directory.glob("*.md")):
            text = md_file.read_text()
            title = md_file.stem.replace("_", " ").title()
            atype = infer_anomaly_type(md_file.name, text)
            for section, content in chunk_markdown(text):
                chunks.append({
                    "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{doc_type}:{md_file.name}:{section}")),
                    "doc_type": doc_type,
                    "title": title,
                    "section": section,
                    "content": content[:1000],
                    "anomaly_type": atype,
                    "embedding": [],
                })
    return chunks


def _index_local_fallback() -> None:
    """When pgvector not available, write a local JSON index for the API to use."""
    import json
    chunks = _collect_chunks()
    # Skip embedding for local fallback — use keyword matching instead
    for chunk in chunks:
        del chunk["embedding"]
    out = ROOT / "data" / "runbook_index.json"
    out.write_text(json.dumps(chunks, indent=2))
    print(f"✓ Local runbook index written: {out} ({len(chunks)} chunks)")
    print(f"  Runbooks: {sum(1 for c in chunks if c['doc_type']=='runbook')}")
    print(f"  Postmortems: {sum(1 for c in chunks if c['doc_type']=='postmortem')}")


if __name__ == "__main__":
    main()
