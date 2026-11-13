"""Store and search vectors using PostgreSQL + pgvector with idempotent upsert and metadata filtering."""
from __future__ import annotations

from contextlib import contextmanager
import json
from typing import Any, Iterator
from urllib.parse import urlparse

from .models import Chunk

ALLOWED_FILTER_COLUMNS: dict[str, str] = {
    "domain": "domain",
    "year": "year",
    "section": "section",
    "version": "version",
    "document_type": "document_type",
    "document_id": "document_id",
}


def _vector_literal(vec: list[float]) -> str:
    return "[" + ",".join(f"{float(v):.8f}" for v in vec) + "]"


class PgVectorStore:
    """PostgreSQL + pgvector store supporting persistent storage, cosine search, and SQL metadata filtering."""

    def __init__(self, database_url: str, dimensions: int = 1536) -> None:
        if not database_url or not database_url.strip():
            raise ValueError("database_url must not be empty")
        if dimensions <= 0:
            raise ValueError("dimensions must be a positive integer")
        self.database_url = database_url.strip()
        self.dimensions = int(dimensions)

    @contextmanager
    def _connect(self) -> Iterator[Any]:
        """Connect using psycopg when available, or fallback to pure-Python pg8000 on Windows AppControl."""
        try:
            import psycopg

            conn = psycopg.connect(self.database_url, connect_timeout=10)
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
            return
        except ImportError:
            pass

        import pg8000.dbapi

        parsed = urlparse(self.database_url)
        conn = pg8000.dbapi.connect(
            user=parsed.username,
            password=parsed.password,
            host=parsed.hostname or "127.0.0.1",
            port=parsed.port or 5432,
            database=(parsed.path or "/").lstrip("/"),
            timeout=10,
        )
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def create_schema(self) -> None:
        """Create pgvector extension, document_chunks table, and metadata/strategy indexes."""
        ddl_statements = [
            "CREATE EXTENSION IF NOT EXISTS vector",
            f"""
            CREATE TABLE IF NOT EXISTS document_chunks (
                strategy TEXT NOT NULL,
                chunk_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                source TEXT NOT NULL,
                page INTEGER NOT NULL,
                domain TEXT,
                year INTEGER,
                version TEXT,
                section TEXT,
                document_type TEXT,
                text TEXT NOT NULL,
                metadata JSONB NOT NULL,
                embedding vector({self.dimensions}) NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (strategy, chunk_id)
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_chunks_strategy_doc ON document_chunks (strategy, document_id)",
            "CREATE INDEX IF NOT EXISTS idx_chunks_strategy_filter ON document_chunks (strategy, domain, year, section)",
        ]
        with self._connect() as conn:
            cur = conn.cursor()
            for stmt in ddl_statements:
                cur.execute(stmt)

    def count_chunks(self, strategy: str | None = None) -> int:
        """Return the number of stored chunks (for a given strategy or total)."""
        with self._connect() as conn:
            cur = conn.cursor()
            if strategy:
                cur.execute("SELECT COUNT(*) FROM document_chunks WHERE strategy = %s", (strategy,))
            else:
                cur.execute("SELECT COUNT(*) FROM document_chunks")
            row = cur.fetchone()
            return int(row[0]) if row else 0

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        """Validate lengths/dimensions, remove obsolete chunks for re-ingested docs, and upsert without duplicates."""
        if not strategy or not strategy.strip():
            raise ValueError("strategy must not be empty")
        if len(chunks) != len(vectors):
            raise ValueError(f"Chunk/vector length mismatch: {len(chunks)} chunks vs {len(vectors)} vectors")
        if not chunks:
            return

        for idx, vec in enumerate(vectors):
            if len(vec) != self.dimensions:
                raise ValueError(
                    f"Vector at index {idx} has dimension {len(vec)}, expected {self.dimensions}"
                )

        # Group incoming chunk_ids by document_id to remove obsolete chunks from modified documents
        incoming_by_doc: dict[str, set[str]] = {}
        for ch in chunks:
            incoming_by_doc.setdefault(ch.document_id, set()).add(ch.chunk_id)

        upsert_sql = """
            INSERT INTO document_chunks (
                strategy, chunk_id, document_id, source, page,
                domain, year, version, section, document_type,
                text, metadata, embedding, updated_at
            )
            VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s::jsonb, %s::vector, NOW()
            )
            ON CONFLICT (strategy, chunk_id) DO UPDATE SET
                document_id = EXCLUDED.document_id,
                source = EXCLUDED.source,
                page = EXCLUDED.page,
                domain = EXCLUDED.domain,
                year = EXCLUDED.year,
                version = EXCLUDED.version,
                section = EXCLUDED.section,
                document_type = EXCLUDED.document_type,
                text = EXCLUDED.text,
                metadata = EXCLUDED.metadata,
                embedding = EXCLUDED.embedding,
                updated_at = NOW()
        """

        with self._connect() as conn:
            cur = conn.cursor()
            # Remove any obsolete chunks belonging to the re-ingested document_ids that are no longer present
            for doc_id, active_ids in incoming_by_doc.items():
                cur.execute(
                    "SELECT chunk_id FROM document_chunks WHERE strategy = %s AND document_id = %s",
                    (strategy, doc_id),
                )
                existing_ids = {row[0] for row in cur.fetchall()}
                obsolete_ids = existing_ids - active_ids
                for obs_id in obsolete_ids:
                    cur.execute(
                        "DELETE FROM document_chunks WHERE strategy = %s AND chunk_id = %s",
                        (strategy, obs_id),
                    )

            for ch, vec in zip(chunks, vectors):
                meta = dict(ch.metadata)
                meta.setdefault("document_id", ch.document_id)
                meta.setdefault("source", ch.source)
                meta.setdefault("page", ch.page)
                cur.execute(
                    upsert_sql,
                    (
                        strategy,
                        ch.chunk_id,
                        ch.document_id,
                        ch.source,
                        int(ch.page),
                        meta.get("domain"),
                        int(meta["year"]) if meta.get("year") is not None else None,
                        str(meta["version"]) if meta.get("version") is not None else None,
                        meta.get("section"),
                        meta.get("document_type"),
                        ch.text,
                        json.dumps(meta, ensure_ascii=False),
                        _vector_literal(vec),
                    ),
                )

    def search(
        self,
        strategy: str,
        query_vector: list[float],
        top_k: int = 3,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Filter permitted metadata in SQL, rank by exact cosine distance (<=>), and return top-k."""
        if len(query_vector) != self.dimensions:
            raise ValueError(
                f"query_vector dimension {len(query_vector)} does not match store dimension {self.dimensions}"
            )
        if top_k <= 0:
            raise ValueError("top_k must be > 0")

        qvec_str = _vector_literal(query_vector)
        where_clauses = ["strategy = %s"]
        params: list[Any] = [qvec_str, strategy]

        if filters:
            for key, val in filters.items():
                if val is None:
                    continue
                col = ALLOWED_FILTER_COLUMNS.get(key)
                if not col:
                    raise ValueError(f"Unsupported or disallowed filter key: {key!r}")
                where_clauses.append(f"{col} = %s")
                params.append(val)

        where_sql = " AND ".join(where_clauses)
        params.extend([qvec_str, int(top_k)])

        query_sql = f"""
            SELECT
                chunk_id,
                document_id,
                source,
                page,
                domain,
                year,
                version,
                section,
                document_type,
                text,
                metadata,
                (embedding <=> %s::vector) AS cosine_distance
            FROM document_chunks
            WHERE {where_sql}
            ORDER BY (embedding <=> %s::vector) ASC, chunk_id ASC
            LIMIT %s
        """

        results: list[dict[str, Any]] = []
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(query_sql, tuple(params))
            rows = cur.fetchall()
            for row in rows:
                (
                    chunk_id,
                    document_id,
                    source,
                    page,
                    domain,
                    year,
                    version,
                    section,
                    document_type,
                    text,
                    raw_meta,
                    cosine_dist,
                ) = row
                if isinstance(raw_meta, str):
                    parsed_meta = json.loads(raw_meta)
                elif isinstance(raw_meta, dict):
                    parsed_meta = dict(raw_meta)
                else:
                    parsed_meta = {}
                parsed_meta.update(
                    {
                        "document_id": document_id,
                        "source": source,
                        "page": int(page),
                        "domain": domain,
                        "year": int(year) if year is not None else None,
                        "version": version,
                        "section": section,
                        "document_type": document_type,
                    }
                )
                dist = float(cosine_dist)
                results.append(
                    {
                        "chunk_id": chunk_id,
                        "document_id": document_id,
                        "source": source,
                        "page": int(page),
                        "text": text,
                        "score": round(1.0 - dist, 6),
                        "cosine_distance": round(dist, 6),
                        "metadata": parsed_meta,
                    }
                )
        return results
