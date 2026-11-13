"""CP3: Run PDF ingestion, normalization, and export two chunking configurations (A: fixed_size, B: by_paragraph)."""
from __future__ import annotations

from dataclasses import asdict
import json
import statistics
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
STARTER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STARTER_DIR))

from src.chunking import by_paragraph, fixed_size  # noqa: E402
from src.ingestion import load_pdf_with_diagnostics  # noqa: E402
from src.models import Chunk  # noqa: E402

CORPUS_FILES = [
    ("nist-ai-rmf-1.0", STARTER_DIR / "data" / "NIST.AI.100-1.pdf", "starter/data/NIST.AI.100-1.pdf"),
    ("nist-csf-2.0", STARTER_DIR / "data" / "NIST.CSWP.29.pdf", "starter/data/NIST.CSWP.29.pdf"),
]

STRATEGY_A_PARAMS = {"method": "fixed_size", "size": 500, "overlap": 50}
STRATEGY_B_PARAMS = {"method": "by_paragraph", "max_size": 900}


def compute_stats(chunks: list[Chunk], params: dict[str, Any]) -> dict[str, Any]:
    lengths = [len(c.text) for c in chunks]
    tokens = [c.metadata["est_tokens"] for c in chunks]
    sorted_lens = sorted(lengths)
    p95_idx = min(len(sorted_lens) - 1, int(round(0.95 * (len(sorted_lens) - 1)))) if sorted_lens else 0

    by_doc: dict[str, int] = {}
    by_domain: dict[str, int] = {}
    for c in chunks:
        by_doc[c.document_id] = by_doc.get(c.document_id, 0) + 1
        dom = str(c.metadata.get("domain", "unknown"))
        by_domain[dom] = by_domain.get(dom, 0) + 1

    # Check how many mid-sentence cuts occur at start/end of chunks (diagnostic for coherence)
    mid_word_or_sentence_cuts = 0
    for c in chunks:
        txt = c.text.strip()
        if txt and not txt.endswith((".", "!", "?", ":", ";", ")")) and not txt[0].isupper():
            mid_word_or_sentence_cuts += 1

    return {
        "parameters": params,
        "chunk_count": len(chunks),
        "total_characters": sum(lengths),
        "total_estimated_tokens": sum(tokens),
        "char_length_distribution": {
            "min": min(lengths) if lengths else 0,
            "p25": sorted_lens[len(sorted_lens) // 4] if sorted_lens else 0,
            "median": round(statistics.median(lengths), 1) if lengths else 0,
            "mean": round(statistics.mean(lengths), 1) if lengths else 0,
            "p75": sorted_lens[(3 * len(sorted_lens)) // 4] if sorted_lens else 0,
            "p95": sorted_lens[p95_idx] if sorted_lens else 0,
            "max": max(lengths) if lengths else 0,
            "stdev": round(statistics.stdev(lengths), 1) if len(lengths) > 1 else 0.0,
        },
        "chunks_by_document": by_doc,
        "chunks_by_domain": by_domain,
        "boundary_cut_count_BothEnds": mid_word_or_sentence_cuts,
    }


def main() -> None:
    all_valid_pages = []
    all_page_logs = []

    for doc_id, abs_path, rel_path in CORPUS_FILES:
        valid_pages, page_logs = load_pdf_with_diagnostics(abs_path, doc_id, rel_path)
        all_valid_pages.extend(valid_pages)
        all_page_logs.extend(page_logs)

    chunks_a: list[Chunk] = []
    chunks_b: list[Chunk] = []

    for page in all_valid_pages:
        chunks_a.extend(fixed_size(page, size=STRATEGY_A_PARAMS["size"], overlap=STRATEGY_A_PARAMS["overlap"]))
        chunks_b.extend(by_paragraph(page, max_size=STRATEGY_B_PARAMS["max_size"]))

    stats_a = compute_stats(chunks_a, STRATEGY_A_PARAMS)
    stats_b = compute_stats(chunks_b, STRATEGY_B_PARAMS)

    results_dir = STARTER_DIR / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    # Save exported chunk configurations
    (results_dir / "chunks_strategy_A.json").write_text(
        json.dumps([asdict(c) for c in chunks_a], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (results_dir / "chunks_strategy_B.json").write_text(
        json.dumps([asdict(c) for c in chunks_b], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    summary = {
        "corpus_valid_pages": len(all_valid_pages),
        "corpus_excluded_pages": sum(1 for p in all_page_logs if p["status"] == "excluded"),
        "strategy_A_fixed_size": stats_a,
        "strategy_B_by_paragraph": stats_b,
        "strategy_C_note": "Strategy C uses the exact same chunks as Strategy B (by_paragraph, max_size=900) and adds metadata filtering at retrieval time.",
    }
    (results_dir / "chunking_stats.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("CP3 Chunking Export Complete:")
    print(f"  - Valid content pages processed: {len(all_valid_pages)} (Excluded logged: {summary['corpus_excluded_pages']})")
    print(
        f"  - Strategy A (fixed_size, size=500, overlap=50): {stats_a['chunk_count']} chunks | "
        f"mean={stats_a['char_length_distribution']['mean']} chars | "
        f"min={stats_a['char_length_distribution']['min']} | max={stats_a['char_length_distribution']['max']} | "
        f"total_chars={stats_a['total_characters']:,} | est_tokens={stats_a['total_estimated_tokens']:,}"
    )
    print(
        f"  - Strategy B (by_paragraph, max_size=900)      : {stats_b['chunk_count']} chunks | "
        f"mean={stats_b['char_length_distribution']['mean']} chars | "
        f"min={stats_b['char_length_distribution']['min']} | max={stats_b['char_length_distribution']['max']} | "
        f"total_chars={stats_b['total_characters']:,} | est_tokens={stats_b['total_estimated_tokens']:,}"
    )


if __name__ == "__main__":
    main()

