"""CP4: Embed chunks with OpenAI text-embedding-3-small, store in PostgreSQL + pgvector for A/B/C, verify idempotent re-ingestion and top-3 retrieval."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
STARTER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STARTER_DIR))

from src.chunking import by_paragraph, fixed_size  # noqa: E402
from src.embeddings import MyEmbedder  # noqa: E402
from src.ingestion import load_pdf  # noqa: E402
from src.models import Chunk  # noqa: E402
from src.store import PgVectorStore  # noqa: E402

CORPUS_FILES = [
    ("nist-ai-rmf-1.0", STARTER_DIR / "data" / "NIST.AI.100-1.pdf", "starter/data/NIST.AI.100-1.pdf"),
    ("nist-csf-2.0", STARTER_DIR / "data" / "NIST.CSWP.29.pdf", "starter/data/NIST.CSWP.29.pdf"),
]


def main() -> None:
    load_dotenv(STARTER_DIR / ".env")
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        sys.exit("DATABASE_URL missing in starter/.env")

    # 1. Load valid pages & build chunks
    t_parse_start = time.perf_counter()
    pages = []
    for doc_id, abs_path, rel_path in CORPUS_FILES:
        pages.extend(load_pdf(abs_path, doc_id, rel_path))
    parse_time_sec = time.perf_counter() - t_parse_start

    t_chunk_a = time.perf_counter()
    chunks_a: list[Chunk] = []
    for p in pages:
        chunks_a.extend(fixed_size(p, size=500, overlap=50))
    chunk_a_time_sec = time.perf_counter() - t_chunk_a

    t_chunk_b = time.perf_counter()
    chunks_b: list[Chunk] = []
    for p in pages:
        chunks_b.extend(by_paragraph(p, max_size=900))
    chunk_b_time_sec = time.perf_counter() - t_chunk_b

    # 2. Initialize real OpenAI embedder and PgVectorStore
    embedder = MyEmbedder(model_name=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"))
    store = PgVectorStore(database_url=db_url, dimensions=embedder.dimensions)
    store.create_schema()

    # 3. Embed Strategy A chunks (383 chunks)
    tokens_before_a = embedder.total_prompt_tokens
    t_emb_a = time.perf_counter()
    vectors_a = embedder.embed_documents([c.text for c in chunks_a], batch_size=64)
    emb_a_time_sec = time.perf_counter() - t_emb_a
    tokens_a = embedder.total_prompt_tokens - tokens_before_a
    cost_a_usd = round((tokens_a / 1_000_000.0) * embedder.price_per_1m_usd, 6)

    t_upsert_a = time.perf_counter()
    store.upsert("A", chunks_a, vectors_a)
    upsert_a_time_sec = time.perf_counter() - t_upsert_a

    # 4. Embed Strategy B chunks (247 chunks)
    tokens_before_b = embedder.total_prompt_tokens
    t_emb_b = time.perf_counter()
    vectors_b = embedder.embed_documents([c.text for c in chunks_b], batch_size=64)
    emb_b_time_sec = time.perf_counter() - t_emb_b
    tokens_b = embedder.total_prompt_tokens - tokens_before_b
    cost_b_usd = round((tokens_b / 1_000_000.0) * embedder.price_per_1m_usd, 6)

    t_upsert_b = time.perf_counter()
    store.upsert("B", chunks_b, vectors_b)
    upsert_b_time_sec = time.perf_counter() - t_upsert_b

    # 5. Upsert Strategy C index (same 247 chunks and vectors as Strategy B, with metadata filter enabled at retrieval)
    t_upsert_c = time.perf_counter()
    store.upsert("C", chunks_b, vectors_b)
    upsert_c_time_sec = time.perf_counter() - t_upsert_c

    # 6. Verify initial counts and idempotent re-ingestion + obsolete chunk cleanup
    counts_initial = {s: store.count_chunks(s) for s in ("A", "B", "C")}

    # Re-ingest same version for A, B, C
    store.upsert("A", chunks_a, vectors_a)
    store.upsert("B", chunks_b, vectors_b)
    store.upsert("C", chunks_b, vectors_b)
    counts_after_reingest = {s: store.count_chunks(s) for s in ("A", "B", "C")}

    # Test obsolete chunk removal when a document changes: insert a temporary obsolete chunk into B, then re-upsert B
    dummy_chunk = Chunk(
        chunk_id="nist-ai-rmf-1.0:p99:para:999",
        document_id="nist-ai-rmf-1.0",
        source="starter/data/NIST.AI.100-1.pdf",
        page=99,
        text="Temporary obsolete chunk to test document update cleanup.",
        metadata={"domain": "ai_risk", "year": 2023, "version": "1.0", "section": "obsolete"},
    )
    store.upsert("B", chunks_b + [dummy_chunk], vectors_b + [vectors_b[0]])
    count_b_with_dummy = store.count_chunks("B")
    store.upsert("B", chunks_b, vectors_b)
    count_b_after_cleanup = store.count_chunks("B")

    # 7. Smoke test top-3 retrieval across A, B, and C (with metadata filter on C)
    sample_question = (
        "Within the AI risk management domain (2023 framework), what contingency and third-party "
        "governance requirements are specified under GOVERN 6?"
    )
    sample_filter = {"domain": "ai_risk", "year": 2023}
    q_vec = embedder.embed_query(sample_question)

    top3_a = store.search("A", q_vec, top_k=3, filters=None)
    top3_b = store.search("B", q_vec, top_k=3, filters=None)
    top3_c = store.search("C", q_vec, top_k=3, filters=sample_filter)

    telemetry = {
        "timestamp": "2026-11-13T17:48:00+07:00",
        "embedding_model": {
            "provider": embedder.provider,
            "model_name": embedder.model_name,
            "dimensions": embedder.dimensions,
            "price_per_1m_tokens_usd": embedder.price_per_1m_usd,
            "query_document_handling": "Symmetric dense embeddings via OpenAI /v1/embeddings (text-embedding-3-small, 1536d) normalized to unit length for cosine distance.",
        },
        "vector_store": {
            "backend": "PostgreSQL + pgvector",
            "postgres_version": "16.16 (Debian 16.16-1.pgdg12+1)",
            "pgvector_version": "0.8.7",
            "table_name": "document_chunks",
            "metric": "cosine (<=> operator in pgvector, score = 1 - cosine_distance)",
            "search_mode": "Exact search (sequential scan over vector(1536) with SQL WHERE pre-filtering on indexed metadata columns)",
            "persistence": "Docker volume day6_student_starter_pg_data mounted at /var/lib/postgresql/data",
        },
        "strategies": {
            "A": {
                "chunking": "fixed_size (size=500, overlap=50)",
                "filter_enabled": False,
                "chunk_count": len(chunks_a),
                "total_characters": sum(len(c.text) for c in chunks_a),
                "prompt_tokens_billed": tokens_a,
                "embedding_api_time_sec": round(emb_a_time_sec, 3),
                "db_upsert_time_sec": round(upsert_a_time_sec, 3),
                "total_ingest_time_sec": round(parse_time_sec + chunk_a_time_sec + emb_a_time_sec + upsert_a_time_sec, 3),
                "cost_usd": cost_a_usd,
            },
            "B": {
                "chunking": "by_paragraph (max_size=900)",
                "filter_enabled": False,
                "chunk_count": len(chunks_b),
                "total_characters": sum(len(c.text) for c in chunks_b),
                "prompt_tokens_billed": tokens_b,
                "embedding_api_time_sec": round(emb_b_time_sec, 3),
                "db_upsert_time_sec": round(upsert_b_time_sec, 3),
                "total_ingest_time_sec": round(parse_time_sec + chunk_b_time_sec + emb_b_time_sec + upsert_b_time_sec, 3),
                "cost_usd": cost_b_usd,
            },
            "C": {
                "chunking": "by_paragraph (max_size=900)",
                "filter_enabled": True,
                "filter_fields": ["domain", "year", "section"],
                "chunk_count": len(chunks_b),
                "total_characters": sum(len(c.text) for c in chunks_b),
                "prompt_tokens_billed_if_standalone": tokens_b,
                "prompt_tokens_billed_reused_from_B": 0,
                "embedding_api_time_sec_if_standalone": round(emb_b_time_sec, 3),
                "db_upsert_time_sec": round(upsert_c_time_sec, 3),
                "total_ingest_time_sec_if_standalone": round(parse_time_sec + chunk_b_time_sec + emb_b_time_sec + upsert_c_time_sec, 3),
                "cost_usd_if_standalone": cost_b_usd,
                "cost_usd_reused_from_B": 0.0,
            },
        },
        "idempotency_and_reingestion_check": {
            "counts_after_first_ingest": counts_initial,
            "counts_after_second_ingest_same_version": counts_after_reingest,
            "zero_duplicates_verified": counts_initial == counts_after_reingest,
            "obsolete_chunk_cleanup_test": {
                "count_with_dummy_obsolete_chunk": count_b_with_dummy,
                "count_after_reingest_cleanup": count_b_after_cleanup,
                "cleanup_verified": (count_b_with_dummy == len(chunks_b) + 1) and (count_b_after_cleanup == len(chunks_b)),
            },
        },
        "smoke_test_top3": {
            "query": sample_question,
            "filter_for_C": sample_filter,
            "A_top3": [
                {"chunk_id": h["chunk_id"], "page": h["page"], "score": h["score"], "domain": h["metadata"]["domain"], "year": h["metadata"]["year"]}
                for h in top3_a
            ],
            "B_top3": [
                {"chunk_id": h["chunk_id"], "page": h["page"], "score": h["score"], "domain": h["metadata"]["domain"], "year": h["metadata"]["year"]}
                for h in top3_b
            ],
            "C_top3": [
                {"chunk_id": h["chunk_id"], "page": h["page"], "score": h["score"], "domain": h["metadata"]["domain"], "year": h["metadata"]["year"]}
                for h in top3_c
            ],
        },
    }

    out_path = STARTER_DIR / "results" / "indexing_telemetry_cp4.json"
    out_path.write_text(json.dumps(telemetry, indent=2, ensure_ascii=False), encoding="utf-8")

    print("CP4 Indexing & Verification Complete:")
    print(f"  - Model: {embedder.provider} / {embedder.model_name} ({embedder.dimensions} dimensions)")
    print(
        f"  - Strategy A: {counts_after_reingest['A']} chunks stored | {tokens_a:,} tokens | "
        f"time={telemetry['strategies']['A']['total_ingest_time_sec']}s | cost=${cost_a_usd:.6f}"
    )
    print(
        f"  - Strategy B: {counts_after_reingest['B']} chunks stored | {tokens_b:,} tokens | "
        f"time={telemetry['strategies']['B']['total_ingest_time_sec']}s | cost=${cost_b_usd:.6f}"
    )
    print(
        f"  - Strategy C: {counts_after_reingest['C']} chunks stored | same embeddings as B | "
        f"standalone time={telemetry['strategies']['C']['total_ingest_time_sec_if_standalone']}s | standalone cost=${cost_b_usd:.6f}"
    )
    print(f"  - Idempotent re-ingestion verified (no duplicates): {telemetry['idempotency_and_reingestion_check']['zero_duplicates_verified']}")
    print(f"  - Obsolete chunk cleanup on doc change verified    : {telemetry['idempotency_and_reingestion_check']['obsolete_chunk_cleanup_test']['cleanup_verified']}")
    print(f"  - Top-3 smoke test A[0]: {top3_a[0]['chunk_id']} (score={top3_a[0]['score']})")
    print(f"  - Top-3 smoke test B[0]: {top3_b[0]['chunk_id']} (score={top3_b[0]['score']})")
    print(f"  - Top-3 smoke test C[0]: {top3_c[0]['chunk_id']} (score={top3_c[0]['score']})")


if __name__ == "__main__":
    main()

