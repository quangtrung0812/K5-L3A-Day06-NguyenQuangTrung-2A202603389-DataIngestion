"""Evaluate retrieved evidence and preserve per-query top-3 traces."""
from __future__ import annotations

import re
from typing import Any


def _norm_ws(text: str) -> str:
    """Collapse whitespace for resilient substring comparison within a single chunk."""
    return re.sub(r"\s+", " ", (text or "")).strip()


def _check_hit_against_gold(
    hit: dict[str, Any],
    gold_source_id: str,
    gold_page: int,
    evidence_quote: str,
) -> tuple[bool, bool]:
    """Return (page_matched, full_evidence_matched) for a single hit against one gold target."""
    page_matched = (hit.get("document_id") == gold_source_id) and (int(hit.get("page", -1)) == int(gold_page))
    if not page_matched:
        return False, False
    hit_text_norm = _norm_ws(hit.get("text", ""))
    quote_norm = _norm_ws(evidence_quote)
    full_evidence_matched = bool(quote_norm and quote_norm in hit_text_norm)
    return True, full_evidence_matched


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    """Check source/page and enough gold evidence; keep hit@1 and hit@3 trace and diagnostics.

    Accepts any documented alternative gold evidence. Does not infer human grounding
    or chunk coherence labels from exact string match.
    """
    top3 = list(hits[:3])
    gold_targets = [
        {
            "gold_source_id": question["gold_source_id"],
            "gold_page": int(question["gold_page"]),
            "evidence_quote": question["evidence_quote"],
            "is_primary": True,
        }
    ]
    for alt in question.get("alternative_gold", []):
        gold_targets.append(
            {
                "gold_source_id": alt["gold_source_id"],
                "gold_page": int(alt["gold_page"]),
                "evidence_quote": alt["evidence_quote"],
                "is_primary": False,
            }
        )

    q_filter: dict[str, Any] | None = question.get("filter")
    annotated_hits: list[dict[str, Any]] = []

    for rank, hit in enumerate(top3, start=1):
        matched_page = False
        matched_evidence = False
        matched_target_info: dict[str, Any] | None = None

        for target in gold_targets:
            p_ok, e_ok = _check_hit_against_gold(
                hit,
                target["gold_source_id"],
                target["gold_page"],
                target["evidence_quote"],
            )
            if p_ok:
                matched_page = True
            if e_ok:
                matched_evidence = True
                matched_target_info = {
                    "gold_source_id": target["gold_source_id"],
                    "gold_page": target["gold_page"],
                    "is_primary": target["is_primary"],
                }
                break

        meta = hit.get("metadata", {})
        if q_filter:
            hit_filter_ok = all(meta.get(k) == v for k, v in q_filter.items())
        else:
            hit_filter_ok = None

        annotated_hits.append(
            {
                "rank": rank,
                "chunk_id": hit.get("chunk_id"),
                "document_id": hit.get("document_id"),
                "source": hit.get("source"),
                "page": hit.get("page"),
                "score": hit.get("score"),
                "cosine_distance": hit.get("cosine_distance"),
                "metadata": meta,
                "text": hit.get("text"),
                "gold_page_match": matched_page,
                "gold_evidence_hit": matched_evidence,
                "matched_gold_target": matched_target_info,
                "filter_compliant": hit_filter_ok,
            }
        )

    hit_at_1 = bool(annotated_hits and annotated_hits[0]["gold_evidence_hit"])
    evidence_hit_at_3 = any(h["gold_evidence_hit"] for h in annotated_hits)
    page_hit_at_1 = bool(annotated_hits and annotated_hits[0]["gold_page_match"])
    page_hit_at_3 = any(h["gold_page_match"] for h in annotated_hits)

    # Check if evidence was split across multiple retrieved chunks from the same gold page
    combined_multi_chunk_hit3 = evidence_hit_at_3
    if not evidence_hit_at_3 and page_hit_at_3:
        for target in gold_targets:
            same_page_texts = [
                h["text"]
                for h in annotated_hits
                if h["document_id"] == target["gold_source_id"] and int(h["page"]) == target["gold_page"]
            ]
            if same_page_texts:
                joined_norm = _norm_ws(" ".join(same_page_texts))
                if _norm_ws(target["evidence_quote"]) in joined_norm:
                    combined_multi_chunk_hit3 = True
                    break

    split_evidence_error = page_hit_at_3 and not evidence_hit_at_3
    if q_filter:
        filter_all_top3_compliant: bool | None = bool(
            annotated_hits and all(h["filter_compliant"] is True for h in annotated_hits)
        )
    else:
        filter_all_top3_compliant = None

    return {
        "question_id": question["id"],
        "split": question["split"],
        "type": question.get("type", "direct"),
        "question": question["question"],
        "expected_answer": question.get("expected_answer"),
        "gold_source_id": question["gold_source_id"],
        "gold_page": int(question["gold_page"]),
        "evidence_quote": question["evidence_quote"],
        "alternative_gold": question.get("alternative_gold", []),
        "query_filter": q_filter,
        "hit_at_1": hit_at_1,
        "evidence_hit_at_3": evidence_hit_at_3,
        "diagnostic_page_hit_at_1": page_hit_at_1,
        "diagnostic_page_hit_at_3": page_hit_at_3,
        "diagnostic_multi_chunk_combined_hit_at_3": combined_multi_chunk_hit3,
        "diagnostic_split_evidence_error": split_evidence_error,
        "filter_all_top3_compliant": filter_all_top3_compliant,
        "top_3_hits": annotated_hits,
    }


def _agg_bucket(items: list[dict[str, Any]]) -> dict[str, Any]:
    n_total = len(items)
    if n_total == 0:
        return {
            "count": 0,
            "hit_at_1": {"hits": 0, "total": 0, "fraction": "0/0", "rate_pct": 0.0},
            "evidence_hit_at_3": {"hits": 0, "total": 0, "fraction": "0/0", "rate_pct": 0.0},
        }

    h1 = sum(1 for x in items if x["hit_at_1"])
    h3 = sum(1 for x in items if x["evidence_hit_at_3"])
    p1 = sum(1 for x in items if x.get("diagnostic_page_hit_at_1"))
    p3 = sum(1 for x in items if x.get("diagnostic_page_hit_at_3"))
    mc3 = sum(1 for x in items if x.get("diagnostic_multi_chunk_combined_hit_at_3"))
    split_errs = [x["question_id"] for x in items if x.get("diagnostic_split_evidence_error")]

    filtered_items = [x for x in items if x.get("query_filter") is not None]
    if filtered_items:
        f_ok = sum(1 for x in filtered_items if x.get("filter_all_top3_compliant") is True)
        f_total = len(filtered_items)
        filter_compliance = {
            "compliant_queries": f_ok,
            "filtered_queries_total": f_total,
            "fraction": f"{f_ok}/{f_total}",
            "rate_pct": round(100.0 * f_ok / f_total, 1),
        }
    else:
        filter_compliance = {
            "compliant_queries": None,
            "filtered_queries_total": 0,
            "fraction": "N/A",
            "rate_pct": None,
        }

    return {
        "count": n_total,
        "hit_at_1": {
            "hits": h1,
            "total": n_total,
            "fraction": f"{h1}/{n_total}",
            "rate_pct": round(100.0 * h1 / n_total, 1),
        },
        "evidence_hit_at_3": {
            "hits": h3,
            "total": n_total,
            "fraction": f"{h3}/{n_total}",
            "rate_pct": round(100.0 * h3 / n_total, 1),
        },
        "diagnostics": {
            "page_hit_at_1_fraction": f"{p1}/{n_total}",
            "page_hit_at_3_fraction": f"{p3}/{n_total}",
            "multi_chunk_combined_hit_at_3_fraction": f"{mc3}/{n_total}",
            "split_evidence_error_count": len(split_errs),
            "split_evidence_question_ids": split_errs,
        },
        "filter_compliance": filter_compliance,
    }


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate Hit@1, Evidence Hit@3, and Filter Compliance by strategy and dev/test split."""
    strategies = sorted({t.get("strategy", "unknown") for t in traces})
    summary: dict[str, Any] = {}

    for strat in strategies:
        strat_traces = [t for t in traces if t.get("strategy") == strat]
        dev_traces = [t for t in strat_traces if t.get("split") == "dev"]
        test_traces = [t for t in strat_traces if t.get("split") == "test"]
        summary[strat] = {
            "dev": _agg_bucket(dev_traces),
            "test": _agg_bucket(test_traces),
            "all": _agg_bucket(strat_traces),
        }

    return summary
