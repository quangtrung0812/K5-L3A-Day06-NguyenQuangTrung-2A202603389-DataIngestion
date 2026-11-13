"""Verify benchmark questions, dev/test split integrity, metadata filters, and exact evidence quotes."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
STARTER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STARTER_DIR))

from src.ingestion import load_pdf  # noqa: E402

CORPUS_MAP = {
    "nist-ai-rmf-1.0": (STARTER_DIR / "data" / "NIST.AI.100-1.pdf", "starter/data/NIST.AI.100-1.pdf"),
    "nist-csf-2.0": (STARTER_DIR / "data" / "NIST.CSWP.29.pdf", "starter/data/NIST.CSWP.29.pdf"),
}
ALLOWED_FILTER_KEYS = {"domain", "year", "section", "version", "document_type"}


def main() -> None:
    bench_path = ROOT_DIR / "benchmark" / "questions.json"
    if not bench_path.exists():
        sys.exit(f"Missing benchmark file: {bench_path}")

    bench = json.loads(bench_path.read_text(encoding="utf-8"))
    questions = bench.get("questions", [])

    # Load all normalized valid pages into memory indexed by (document_id, page_number)
    page_index = {}
    for doc_id, (abs_path, rel_path) in CORPUS_MAP.items():
        for page_obj in load_pdf(abs_path, doc_id, rel_path):
            page_index[(doc_id, page_obj.page)] = page_obj

    dev_qs = [q for q in questions if q["split"] == "dev"]
    test_qs = [q for q in questions if q["split"] == "test"]
    filter_qs = [q for q in questions if q.get("filter")]
    test_filter_qs = [q for q in test_qs if q.get("filter")]

    errors: list[str] = []
    verification_records = []

    if len(questions) < 20:
        errors.append(f"Total questions {len(questions)} < 20")
    if len(dev_qs) < 15:
        errors.append(f"Dev questions {len(dev_qs)} < 15")
    if len(test_qs) < 5:
        errors.append(f"Test questions {len(test_qs)} < 5")
    if len(filter_qs) < 3:
        errors.append(f"Filtered questions {len(filter_qs)} < 3")
    if len(test_filter_qs) < 1:
        errors.append(f"Test filtered questions {len(test_filter_qs)} < 1")

    dev_pages = {(q["gold_source_id"], q["gold_page"]) for q in dev_qs}
    test_pages = {(q["gold_source_id"], q["gold_page"]) for q in test_qs}
    overlapping_pages = dev_pages & test_pages
    if overlapping_pages:
        errors.append(f"Data leakage warning: overlapping primary gold pages between dev and test: {overlapping_pages}")

    for q in questions:
        qid = q["id"]
        key = (q["gold_source_id"], q["gold_page"])
        if key not in page_index:
            errors.append(f"[{qid}] Gold page {key} is not a valid content page!")
            continue

        page_obj = page_index[key]
        quote = q["evidence_quote"]
        primary_found = quote in page_obj.text
        if not primary_found:
            errors.append(f"[{qid}] Primary evidence_quote not found on {key}: {quote!r}")

        alt_checks = []
        for alt in q.get("alternative_gold", []):
            alt_key = (alt["gold_source_id"], alt["gold_page"])
            alt_page = page_index.get(alt_key)
            alt_found = bool(alt_page and alt["evidence_quote"] in alt_page.text)
            if not alt_found:
                errors.append(f"[{qid}] Alternative evidence_quote not found on {alt_key}: {alt['evidence_quote']!r}")
            alt_checks.append({"source_id": alt["gold_source_id"], "page": alt["gold_page"], "verified": alt_found})

        q_filter = q.get("filter")
        filter_valid = True
        if q_filter is not None:
            for fk, fv in q_filter.items():
                if fk not in ALLOWED_FILTER_KEYS:
                    errors.append(f"[{qid}] Disallowed filter key {fk!r} (potential leakage)")
                    filter_valid = False
                elif page_obj.metadata.get(fk) != fv:
                    errors.append(
                        f"[{qid}] Filter {fk}={fv!r} does not match page metadata {page_obj.metadata.get(fk)!r}"
                    )
                    filter_valid = False

        verification_records.append(
            {
                "id": qid,
                "split": q["split"],
                "type": q["type"],
                "gold_source_id": q["gold_source_id"],
                "gold_page": q["gold_page"],
                "gold_section": page_obj.metadata["section"],
                "primary_evidence_verified": primary_found,
                "evidence_char_length": len(quote),
                "alternative_gold_verified": alt_checks,
                "has_filter": q_filter is not None,
                "filter": q_filter,
                "filter_verified_against_source": filter_valid,
            }
        )

    if errors:
        for err in errors:
            print("ERROR:", err)
        sys.exit(f"Benchmark verification failed with {len(errors)} error(s).")

    report = {
        "status": "VERIFIED_OK",
        "total_questions": len(questions),
        "dev_count": len(dev_qs),
        "test_count": len(test_qs),
        "filtered_total": len(filter_qs),
        "filtered_dev": len(filter_qs) - len(test_filter_qs),
        "filtered_test": len(test_filter_qs),
        "dev_test_primary_page_overlap": len(overlapping_pages),
        "records": verification_records,
    }

    out_path = STARTER_DIR / "results" / "benchmark_verification_report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("Benchmark verification PASSED (0 errors):")
    print(f"  - Total questions     : {report['total_questions']} (Dev: {report['dev_count']}, Test: {report['test_count']})")
    print(f"  - Filtered questions  : {report['filtered_total']} (Dev: {report['filtered_dev']}, Test: {report['filtered_test']})")
    print(f"  - Dev/Test page overlap: {report['dev_test_primary_page_overlap']} pages")
    print(f"  - All 20 primary evidence quotes + {sum(len(r['alternative_gold_verified']) for r in verification_records)} alternative quotes verified verbatim in normalized PDF pages.")
    print(f"  - Report saved to     : {out_path}")


if __name__ == "__main__":
    main()

