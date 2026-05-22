"""
pgvector Client
===============
psycopg2 connection pool + pgvector helper methods.
DSN loaded from SSM: /sovereign-sre/rds-connection-string
or from env RDS_CONNECTION_STRING.

# RDS COST: db.t3.micro = FREE TIER (750 hrs/month for 12 months)
"""


from __future__ import annotations
import json
import os
from contextlib import contextmanager
from typing import Optional

from aws.config import REGION


def _get_dsn() -> str:
    dsn = os.environ.get("RDS_CONNECTION_STRING", "")
    if not dsn:
        host = os.environ.get("RDS_HOST", "localhost")
        port = os.environ.get("RDS_PORT", "5432")
        db = os.environ.get("RDS_DB", "sovereignsre")
        user = os.environ.get("RDS_USER", "sreadmin")
        pwd = os.environ.get("RDS_PASSWORD", "")
        dsn = f"postgresql://{user}:{pwd}@{host}:{port}/{db}"
    return dsn


class PgVectorClient:
    def __init__(self, dsn: Optional[str] = None):
        self._dsn = dsn or _get_dsn()
        self._pool = None

    def _get_pool(self):
        if self._pool is None:
            from psycopg2 import pool as pg_pool
            self._pool = pg_pool.ThreadedConnectionPool(1, 10, self._dsn)
        return self._pool

    @contextmanager
    def _conn(self):
        pool = self._get_pool()
        conn = pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            pool.putconn(conn)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def upsert_embedding(
        self,
        file_path: str,
        chunk_index: int,
        content: str,
        embedding: list[float],
        metadata: Optional[dict] = None,
        language: Optional[str] = None,
    ) -> None:
        sql = """
        INSERT INTO code_embeddings
            (file_path, chunk_index, language, content, embedding, metadata)
        VALUES (%s, %s, %s, %s, %s::vector, %s)
        ON CONFLICT (file_path, chunk_index) DO UPDATE SET
            content   = EXCLUDED.content,
            embedding = EXCLUDED.embedding,
            metadata  = EXCLUDED.metadata,
            language  = EXCLUDED.language
        """
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (
                    file_path,
                    chunk_index,
                    language,
                    content,
                    str(embedding),
                    json.dumps(metadata or {}),
                ))

    def delete_file_embeddings(self, file_path: str) -> None:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM code_embeddings WHERE file_path = %s",
                    (file_path,),
                )

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filter_language: Optional[str] = None,
    ) -> list[dict]:
        where = "WHERE language = %s" if filter_language else ""
        sql = f"""
        SELECT file_path, chunk_index, language, content, metadata,
               1 - (embedding <=> %s::vector) AS score
        FROM code_embeddings
        {where}
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """
        params = [str(query_embedding)]
        if filter_language:
            params.append(filter_language)
        params.extend([str(query_embedding), top_k])

        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()

        results = []
        for row in rows:
            results.append({
                "file_path": row[0],
                "chunk_index": row[1],
                "language": row[2],
                "content": row[3],
                "metadata": row[4] if isinstance(row[4], dict) else json.loads(row[4] or "{}"),
                "score": float(row[5]),
            })
        return results

    def health_check(self) -> bool:
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            return True
        except Exception:
            return False

    def get_chunk_count(self) -> int:
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM code_embeddings")
                    return cur.fetchone()[0]
        except Exception:
            return 0
