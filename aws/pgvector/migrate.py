"""
ChromaDB → pgvector Migration
==============================
One-time migration: reads existing ChromaDB collections,
re-embeds with BGE-M3, inserts into pgvector.
Idempotent: skips already-migrated chunks (UNIQUE constraint).

Usage:
    python aws/pgvector/migrate.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

from aws.pgvector.client import PgVectorClient

console = Console()

CHROMA_HOST = os.environ.get("CHROMA_HOST", "http://localhost:8000")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "BAAI/bge-m3")
COLLECTION_NAME = os.environ.get("CHROMA_COLLECTION_NAME", "sovereign_sre_codebase")


def migrate() -> int:
    """Returns count of migrated chunks."""
    console.rule("[bold cyan]ChromaDB → pgvector migration[/]")

    # 1. Connect to ChromaDB
    try:
        import chromadb
        host = CHROMA_HOST.replace("http://", "").replace("https://", "")
        if ":" in host:
            h, p = host.split(":")
            chroma_client = chromadb.HttpClient(host=h, port=int(p))
        else:
            chroma_client = chromadb.HttpClient(host=host, port=8000)

        collection = chroma_client.get_collection(name=COLLECTION_NAME)
        total = collection.count()
        console.print(f"[green]ChromaDB connected:[/] {total} chunks in '{COLLECTION_NAME}'")
    except Exception as e:
        console.print(f"[red]Cannot connect to ChromaDB:[/] {e}")
        console.print("[yellow]Skipping migration (ChromaDB not available)[/]")
        return 0

    if total == 0:
        console.print("[yellow]Nothing to migrate — ChromaDB collection is empty.[/]")
        return 0

    # 2. Load embedding model
    console.print(f"Loading embedding model: {EMBED_MODEL} ...")
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    embed = HuggingFaceEmbedding(model_name=EMBED_MODEL)

    # 3. Connect to pgvector
    pg = PgVectorClient()
    if not pg.health_check():
        console.print("[red]pgvector not reachable — check RDS_CONNECTION_STRING[/]")
        return 0

    # 4. Migrate in batches
    batch_size = 100
    migrated = 0
    skipped = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task("Migrating chunks", total=total)

        offset = 0
        while offset < total:
            result = collection.get(
                limit=batch_size,
                offset=offset,
                include=["documents", "metadatas"],
            )

            ids = result.get("ids", [])
            docs = result.get("documents", [])
            metas = result.get("metadatas", [])

            for idx, (doc_id, content, meta) in enumerate(zip(ids, docs, metas)):
                if not content or not content.strip():
                    skipped += 1
                    continue

                file_path = meta.get("file_path", f"unknown/{doc_id}")
                chunk_index = meta.get("chunk_index", idx)
                language = meta.get("language", "")

                try:
                    embedding = embed.get_text_embedding(content)
                    pg.upsert_embedding(
                        file_path=file_path,
                        chunk_index=int(chunk_index),
                        content=content,
                        embedding=embedding,
                        metadata=meta,
                        language=language,
                    )
                    migrated += 1
                except Exception as e:
                    console.print(f"[dim red]Skip {file_path}[{chunk_index}]: {e}[/]")
                    skipped += 1

            offset += batch_size
            progress.update(task, completed=min(offset, total))

    console.print(f"\n[bold green]Migration complete:[/] {migrated} migrated, {skipped} skipped")
    console.print(f"pgvector total: {pg.get_chunk_count()} chunks")
    return migrated


if __name__ == "__main__":
    migrate()
