"""Main pipeline entry point: validate corpus, ensure A/B/C indexes, run dev/test benchmark, and save traces."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .chunking import by_paragraph, fixed_size
from .embeddings import MyEmbedder
from .evaluation import evaluate_query, summarize
from .ingestion import load_pdf_with_diagnostics
from .models import Chunk
from .store import PgVectorStore

STARTER_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = STARTER_DIR.parent

CORPUS_FILES = [
    ("nist-ai-rmf-1.0", STARTER_DIR / "data" / "NIST.AI.100-1.pdf", "starter/data/NIST.AI.100-1.pdf"),
    ("nist-csf-2.0", STARTER_DIR / "data" / "NIST.CSWP.29.pdf", "starter/data/NIST.CSWP.29.pdf"),
]


def main() -> None:
    load_dotenv(STARTER_DIR / ".env")
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        sys.exit("DATABASE_URL missing in starter/.env")

    # 1. Load and validate corpus (>= 30 valid content pages)
    all_pages = []
    all_logs = []
    for doc_id, abs_path, rel_path in CORPUS_FILES:
        valid_pages, page_logs = load_pdf_with_diagnostics(abs_path, doc_id, rel_path)
        all_pages.extend(valid_pages)
        all_logs.extend(page_logs)

    if len(all_pages) < 30:
        raise RuntimeError(f"Corpus validation failed: {len(all_pages)} valid pages (< 30 required)")

    # 2. Build chunks for Strategies A and B/C
    chunks_a: list[Chunk] = []
    chunks_b: list[Chunk] = []
    for page in all_pages:
        chunks_a.extend(fixed_size(page, size=500, overlap=50))
        chunks_b.extend(by_paragraph(page, max_size=900))

    # 3. Initialize embedder and vector store; ensure all three strategy indexes are populated
    embedder = MyEmbedder(model_name=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"))
    store = PgVectorStore(database_url=db_url, dimensions=embedder.dimensions)
    store.create_schema()

    if store.count_chunks("A") != len(chunks_a):
        vecs_a = embedder.embed_documents([c.text for c in chunks_a], batch_size=64)
        store.upsert("A", chunks_a, vecs_a)

    if store.count_chunks("B") != len(chunks_b) or store.count_chunks("C") != len(chunks_b):
        vecs_b = embedder.embed_documents([c.text for c in chunks_b], batch_size=64)
        store.upsert("B", chunks_b, vecs_b)
        store.upsert("C", chunks_b, vecs_b)

    # 4. Load benchmark questions and embed all 20 queries once using the same model
    bench_path = ROOT_DIR / "benchmark" / "questions.json"
    bench_data = json.loads(bench_path.read_text(encoding="utf-8"))
    questions: list[dict[str, Any]] = bench_data["questions"]

    q_tokens_before = embedder.total_prompt_tokens
    t_q_emb = time.perf_counter()
    query_vectors = embedder.embed_documents([q["question"] for q in questions], batch_size=32)
    q_emb_time_sec = time.perf_counter() - t_q_emb
    q_tokens = embedder.total_prompt_tokens - q_tokens_before
    q_cost_usd = round((q_tokens / 1_000_000.0) * embedder.price_per_1m_usd, 8)

    # 5. Run top-3 retrieval across Strategies A, B, and C
    all_traces: list[dict[str, Any]] = []
    search_timings_sec: dict[str, float] = {"A": 0.0, "B": 0.0, "C": 0.0}

    for strategy in ("A", "B", "C"):
        t_s0 = time.perf_counter()
        for q, q_vec in zip(questions, query_vectors):
            applied_filter = q.get("filter") if strategy == "C" else None
            hits = store.search(strategy=strategy, query_vector=q_vec, top_k=3, filters=applied_filter)
            trace = evaluate_query(q, hits)
            trace["strategy"] = strategy
            trace["filter_mode"] = (
                "metadata_filter_applied"
                if (strategy == "C" and applied_filter is not None)
                else ("unfiltered_query_in_C" if strategy == "C" else "no_filter_strategy")
            )
            trace["applied_filter"] = applied_filter
            all_traces.append(trace)
        search_timings_sec[strategy] = round(time.perf_counter() - t_s0, 4)

    summary_metrics = summarize(all_traces)

    results_dir = STARTER_DIR / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    traces_output = {
        "benchmark_name": bench_data["benchmark_name"],
        "embedding_model": embedder.model_name,
        "dimensions": embedder.dimensions,
        "query_embedding_tokens": q_tokens,
        "query_embedding_time_sec": round(q_emb_time_sec, 4),
        "query_embedding_cost_usd": q_cost_usd,
        "search_timings_sec": search_timings_sec,
        "traces": all_traces,
    }
    (results_dir / "retrieval_traces_top3.json").write_text(
        json.dumps(traces_output, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    summary_output = {
        "benchmark_name": bench_data["benchmark_name"],
        "selection_criteria_locked_before_test": bench_data.get("selection_criteria_locked_before_test"),
        "query_telemetry": {
            "total_questions": len(questions),
            "query_prompt_tokens": q_tokens,
            "query_embedding_time_sec": round(q_emb_time_sec, 4),
            "query_embedding_cost_usd": q_cost_usd,
            "db_search_time_sec_per_strategy": search_timings_sec,
        },
        "metrics_by_strategy": summary_metrics,
    }
    (results_dir / "benchmark_summary_metrics.json").write_text(
        json.dumps(summary_output, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("=== Day 06 Retrieval Benchmark Summary ===")
    for strat in ("A", "B", "C"):
        m_dev = summary_metrics[strat]["dev"]
        m_test = summary_metrics[strat]["test"]
        m_all = summary_metrics[strat]["all"]
        print(
            f"Strategy {strat} | "
            f"DEV: Hit@1={m_dev['hit_at_1']['fraction']} ({m_dev['hit_at_1']['rate_pct']}%), "
            f"Hit@3={m_dev['evidence_hit_at_3']['fraction']} ({m_dev['evidence_hit_at_3']['rate_pct']}%), "
            f"Filter={m_dev['filter_compliance']['fraction']} | "
            f"TEST: Hit@1={m_test['hit_at_1']['fraction']} ({m_test['hit_at_1']['rate_pct']}%), "
            f"Hit@3={m_test['evidence_hit_at_3']['fraction']} ({m_test['evidence_hit_at_3']['rate_pct']}%), "
            f"Filter={m_test['filter_compliance']['fraction']} | "
            f"ALL: Hit@1={m_all['hit_at_1']['fraction']}, Hit@3={m_all['evidence_hit_at_3']['fraction']}"
        )


if __name__ == "__main__":
    main()
