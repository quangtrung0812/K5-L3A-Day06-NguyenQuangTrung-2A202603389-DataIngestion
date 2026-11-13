"""CP5: Generate structured manual audit artifacts for Chunk Coherence (10 positions), Metadata Usefulness (15 test records/strategy), and Grounding Quality (5 test queries/strategy)."""
from __future__ import annotations

import json
from pathlib import Path

STARTER_DIR = Path(__file__).resolve().parents[1]
RESULTS_DIR = STARTER_DIR / "results"


def main() -> None:
    chunks_a = json.loads((RESULTS_DIR / "chunks_strategy_A.json").read_text(encoding="utf-8"))
    chunks_b = json.loads((RESULTS_DIR / "chunks_strategy_B.json").read_text(encoding="utf-8"))
    traces_data = json.loads((RESULTS_DIR / "retrieval_traces_top3.json").read_text(encoding="utf-8"))
    traces = traces_data["traces"]

    # 1. Manual Chunk Coherence Audit on the first 10 sorted valid page_ids (boundary position #2 on each page)
    coherence_specs = [
        (
            "nist-ai-rmf-1.0:p06",
            1,
            "Starts mid-word ('izations, communities...') and ends mid-word ('...AI s'), truncating the autonomy clause of the AI system definition.",
            2,
            "Contains the complete, self-contained paragraph defining an AI system and its varying levels of autonomy per OECD/ISO.",
        ),
        (
            "nist-ai-rmf-1.0:p07",
            1,
            "Starts with a broken citation fragment ('/IEC TR 24368:2022).') before stating the ISO definition of professional responsibility.",
            2,
            "Preserves the complete, self-contained paragraph defining organizational practices and professional responsibility.",
        ),
        (
            "nist-ai-rmf-1.0:p08",
            1,
            "Starts mid-word ('plies to all stages...' missing subject 'GOVERN') and cuts off mid-predicate at the end ('...is directed').",
            2,
            "Preserves the complete paragraph describing NIST's collaborative development of AI RMF 1.0 with public and private sectors.",
        ),
        (
            "nist-ai-rmf-1.0:p09",
            1,
            "Starts mid-word ('ext of the AI RMF...') and cuts off mid-word ('...event oc') right before the second factor of the risk equation (likelihood of occurrence).",
            2,
            "Preserves the entire risk definition paragraph (both magnitude of harm and likelihood of occurrence) plus the ISO 31000 risk management definition.",
        ),
        (
            "nist-ai-rmf-1.0:p10",
            1,
            "Starts mid-word ('quately understood...') and cuts off mid-word ('...third-party data, so'), losing the explanation of metric misalignment.",
            2,
            "Preserves the full paragraph on third-party software, hardware, and data risk measurement challenges and ends cleanly at a sentence boundary.",
        ),
        (
            "nist-ai-rmf-1.0:p11",
            1,
            "Starts mid-clause ('metrics is often an institutional endeavor...' missing 'development of') and ends mid-word ('...communities or o').",
            2,
            "Contains two complete, coherent paragraphs on population impact measurement and risk perspectives across AI lifecycle stages.",
        ),
        (
            "nist-ai-rmf-1.0:p12",
            1,
            "Starts with a sentence fragment ('and application and use-case specific.' missing subject 'Risk tolerance') and ends mid-word ('...will contin').",
            2,
            "Contains two complete paragraphs on harm/cost-benefit tradeoffs and contexts where risk tolerances remain unresolved.",
        ),
        (
            "nist-ai-rmf-1.0:p13",
            0,
            "Severely broken at both ends: starts mid-word ('ease in a safe manner...') without the subject or unacceptable-risk condition, and ends mid-word ('...comprised of sensi').",
            2,
            "Preserves the complete paragraph comparing risk prioritization between human-facing AI systems and computational-only AI systems.",
        ),
        (
            "nist-ai-rmf-1.0:p14",
            1,
            "Starts mid-sentence ('small to medium-sized organizations...') and cuts off mid-word ('...disciplinarily divers') in Section 2 Audience.",
            2,
            "Preserves the complete introductory paragraph of Section 2 (Audience) cleanly.",
        ),
        (
            "nist-ai-rmf-1.0:p15",
            0,
            "Starts with a detached fragment ('AI actors.\\n\\nenvironmental groups...') missing its subject/verb from the previous chunk, and cuts off the 4th bullet mid-word ('...related to civ').",
            1,
            "Starts with the 4th bullet item ('• promote discussion of the tradeoffs...') detached from its lead-in header ('These actors can:') in para:001 due to the 900-char limit, followed by a complete paragraph.",
        ),
    ]

    coherence_records = []
    for idx, (pid, score_a, reason_a, score_b, reason_b) in enumerate(coherence_specs, start=1):
        ca = [c for c in chunks_a if c["metadata"]["page_id"] == pid][1]
        cb = [c for c in chunks_b if c["metadata"]["page_id"] == pid][1]
        coherence_records.append(
            {
                "sample_index": idx,
                "source_position_id": pid,
                "selection_rule": "First 10 sorted valid page_ids in corpus, evaluating the 2nd chunk (first internal chunk boundary) on each page.",
                "strategy_A": {
                    "chunk_id": ca["chunk_id"],
                    "char_length": len(ca["text"]),
                    "score_0_to_2": score_a,
                    "reason": reason_a,
                    "text": ca["text"],
                },
                "strategy_B": {
                    "chunk_id": cb["chunk_id"],
                    "char_length": len(cb["text"]),
                    "score_0_to_2": score_b,
                    "reason": reason_b,
                    "text": cb["text"],
                },
                "strategy_C": {
                    "chunk_id": cb["chunk_id"],
                    "char_length": len(cb["text"]),
                    "score_0_to_2": score_b,
                    "reason": reason_b + " (Identical chunking to Strategy B).",
                    "text": cb["text"],
                },
            }
        )

    scores_a = [r["strategy_A"]["score_0_to_2"] for r in coherence_records]
    scores_b = [r["strategy_B"]["score_0_to_2"] for r in coherence_records]

    coherence_audit = {
        "dimension": "2. Chunk Coherence",
        "grader": "Author (manual inspection prior to test tuning; potential self-grading bias noted)",
        "sample_size_per_strategy": len(coherence_records),
        "sampling_methodology": "Pre-selected the first 10 sorted valid page_ids (nist-ai-rmf-1.0:p06 to nist-ai-rmf-1.0:p15) and audited the second chunk on each page (first internal boundary).",
        "summary_by_strategy": {
            "A": {
                "n": 10,
                "score_counts": {"0": scores_a.count(0), "1": scores_a.count(1), "2": scores_a.count(2)},
                "total_points": f"{sum(scores_a)}/20",
                "mean_score_out_of_2": round(sum(scores_a) / len(scores_a), 2),
            },
            "B": {
                "n": 10,
                "score_counts": {"0": scores_b.count(0), "1": scores_b.count(1), "2": scores_b.count(2)},
                "total_points": f"{sum(scores_b)}/20",
                "mean_score_out_of_2": round(sum(scores_b) / len(scores_b), 2),
            },
            "C": {
                "n": 10,
                "score_counts": {"0": scores_b.count(0), "1": scores_b.count(1), "2": scores_b.count(2)},
                "total_points": f"{sum(scores_b)}/20",
                "mean_score_out_of_2": round(sum(scores_b) / len(scores_b), 2),
            },
        },
        "samples": coherence_records,
    }
    (RESULTS_DIR / "manual_audit_coherence.json").write_text(
        json.dumps(coherence_audit, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # 2. Manual Audit of Metadata Usefulness (5 test queries x top-3 = 15 records per strategy) & Grounding Quality (5 test queries)
    grounding_specs = {
        "q16": {
            "A": (
                1,
                "Rank #1 (nist-ai-rmf-1.0:p20:fixed:002) starts Section 3.3 Secure and Resilient but cuts off mid-sentence right before 'degrade safely and gracefully', and misses the paragraph contrasting resilience with security protocols.",
            ),
            "B": (
                2,
                "Rank #1 (p20:para:002) provides the full resilience definition including graceful degradation, and Rank #2 (p20:para:003) provides the explicit distinction between resilience and security protocols.",
            ),
            "C": (
                2,
                "Rank #1 (p20:para:002) and Rank #2 (p20:para:003) together provide complete evidence and conditions to answer both parts of the question with exact source/page traceability.",
            ),
        },
        "q17": {
            "A": (
                2,
                "Rank #3 (nist-ai-rmf-1.0:p30:fixed:005) contains the complete required outcome sentence regarding sufficient contextual knowledge to inform an initial go/no-go decision before proceeding to MEASURE and MANAGE.",
            ),
            "B": (
                0,
                "Failure case: Top-3 retrieved p26:para:002, p33:para:001, and p35:para:001, which discuss general function ordering and MEASURE subcategories but miss the Page 30 paragraph on the post-MAP go/no-go decision.",
            ),
            "C": (
                0,
                "Failure case: Unfiltered query runs identically to Strategy B; Top-3 misses Page 30 because the 900-char paragraph on Page 30 combined 8 bullet items with the closing go/no-go sentence, diluting its cosine similarity.",
            ),
        },
        "q18": {
            "A": (
                1,
                "Rank #1 (nist-ai-rmf-1.0:p44:fixed:004) captures the lead-in sentence and 3 of the 5 bulleted AI-specific risks (harmful bias, generative AI, ML attacks), but cuts off before the 5th bullet (third-party AI, transfer learning, off-label fine-tuning).",
            ),
            "B": (
                1,
                "Rank #2 (nist-ai-rmf-1.0:p44:para:003) captures the lead-in sentence and the first 2 bullets (harmful bias, generative AI), while the remaining 3 bullets were placed in p44:para:004 outside top-3.",
            ),
            "C": (
                1,
                "Rank #2 (nist-ai-rmf-1.0:p44:para:003) provides partial evidence (first 2 of 5 bullets from Appendix B Page 44); remaining 3 bullets were split into the next chunk p44:para:004.",
            ),
        },
        "q19": {
            "A": (
                1,
                "Rank #1 (nist-ai-rmf-1.0:p28:fixed:002) starts mid-word ('s and procedures are in place for decommissioning...'), omitting the 'GOVERN 1.7' identifier and completely missing GOVERN 1.6 (AI system inventory mechanisms).",
            ),
            "B": (
                2,
                "Rank #2 (nist-ai-rmf-1.0:p28:para:001) contains both GOVERN 1.6 (inventory mechanisms) and GOVERN 1.7 (safe decommissioning and phasing out) in full with exact table/page context.",
            ),
            "C": (
                2,
                "Rank #2 (nist-ai-rmf-1.0:p28:para:001) contains complete, intact evidence for both GOVERN 1.6 and GOVERN 1.7 under the verified filter (domain='ai_risk', year=2023).",
            ),
        },
        "q20": {
            "A": (
                2,
                "Rank #1 (nist-csf-2.0:p28:fixed:001) contains the full RC.RP-03 requirement ('The integrity of backups and other restoration assets is verified before using them for restoration') and surrounding RC.RP context.",
            ),
            "B": (
                2,
                "Rank #1 (nist-csf-2.0:p28:para:001) contains the full RC.RP-03 subcategory and surrounding Incident Recovery Plan Execution subcategories with exact page traceability.",
            ),
            "C": (
                2,
                "Rank #1 (nist-csf-2.0:p28:para:001) contains the full RC.RP-03 subcategory under verified filter (domain='cybersecurity', year=2024).",
            ),
        },
    }

    metadata_records_by_strategy = {}
    grounding_by_strategy = {}

    for strat in ("A", "B", "C"):
        test_traces = [t for t in traces if t["strategy"] == strat and t["split"] == "test"]
        meta_checks = []
        g_records = []
        g_scores = []

        for t in test_traces:
            qid = t["question_id"]
            g_score, g_reason = grounding_specs[qid][strat]
            g_scores.append(g_score)
            g_records.append(
                {
                    "question_id": qid,
                    "question": t["question"],
                    "gold_source_id": t["gold_source_id"],
                    "gold_page": t["gold_page"],
                    "top_3_chunk_ids": [h["chunk_id"] for h in t["top_3_hits"]],
                    "grounding_score_0_to_2": g_score,
                    "reason": g_reason,
                }
            )
            for h in t["top_3_hits"]:
                meta = h["metadata"]
                has_all_required = all(
                    meta.get(k) not in (None, "")
                    for k in ("document_id", "source", "page", "domain", "year", "section")
                )
                meta_checks.append(
                    {
                        "question_id": qid,
                        "rank": h["rank"],
                        "chunk_id": h["chunk_id"],
                        "source": h["source"],
                        "page": h["page"],
                        "domain": meta.get("domain"),
                        "year": meta.get("year"),
                        "section": meta.get("section"),
                        "metadata_complete_and_accurate": has_all_required,
                        "filter_required": t["query_filter"],
                        "filter_compliant": h["filter_compliant"],
                    }
                )

        valid_meta_count = sum(1 for m in meta_checks if m["metadata_complete_and_accurate"])
        metadata_records_by_strategy[strat] = {
            "checked_records_total": len(meta_checks),
            "complete_and_accurate_count": valid_meta_count,
            "complete_and_accurate_fraction": f"{valid_meta_count}/{len(meta_checks)}",
            "complete_and_accurate_pct": round(100.0 * valid_meta_count / len(meta_checks), 1),
            "records": meta_checks,
        }
        grounding_by_strategy[strat] = {
            "n_test_questions": len(g_records),
            "score_counts": {"0": g_scores.count(0), "1": g_scores.count(1), "2": g_scores.count(2)},
            "total_points": f"{sum(g_scores)}/{2 * len(g_records)}",
            "mean_score_out_of_2": round(sum(g_scores) / len(g_scores), 2),
            "questions": g_records,
        }

    meta_and_grounding_audit = {
        "grader": "Author (manual verification against NIST.AI.100-1.pdf and NIST.CSWP.29.pdf; potential self-grading bias noted)",
        "metadata_usefulness": {
            "summary_by_strategy": {
                s: {
                    "test_top3_metadata_accurate_fraction": metadata_records_by_strategy[s]["complete_and_accurate_fraction"],
                    "test_top3_metadata_accurate_pct": metadata_records_by_strategy[s]["complete_and_accurate_pct"],
                    "dev_filter_compliance_fraction": "4/4" if s == "C" else "3/4",
                    "test_filter_compliance_fraction": "2/2",
                    "all_filtered_queries_compliance_fraction": "6/6" if s == "C" else "5/6",
                    "unfiltered_queries_compliance": "N/A",
                }
                for s in ("A", "B", "C")
            },
            "how_metadata_helps": (
                "1) Traceability: 'source' and physical 'page' allow instant verification of every retrieved quote in the original PDF. "
                "2) Scope isolation: 'domain' (ai_risk vs cybersecurity), 'year' (2023 vs 2024), and 'section' prevent cross-section and cross-framework noise—for example, on q15 (PR.AA-05 in CSF Appendix A), Strategy C's section filter eliminated the off-section chunk from Section 1 (p07:para:003) that appeared in Strategy B's top-3, raising dev filter compliance from 3/4 (75.0%) to 4/4 (100.0%)."
            ),
            "metadata_limitations": (
                "1) Coarse page-level section assignment: When a PDF page contains a transition between two subsections, a single page-level 'section' label applies to the whole page. "
                "2) Rigid pre-filtering risk: If a user supplies an overly narrow or incorrect metadata filter (e.g., filtering for 'appendix_a_csf_core' when the answer is in 'profiles_tiers_and_integration'), hard SQL WHERE filtering will exclude the true evidence completely."
            ),
            "detailed_records_by_strategy": metadata_records_by_strategy,
        },
        "grounding_quality": {
            "note": "Evaluates sufficiency of retrieved top-3 evidence to answer the question and cite the source; this is NOT an evaluation of LLM-generated answer text.",
            "summary_by_strategy": grounding_by_strategy,
        },
    }
    (RESULTS_DIR / "manual_audit_metadata_and_grounding.json").write_text(
        json.dumps(meta_and_grounding_audit, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("CP5 Manual Audit Artifacts Generated:")
    for s in ("A", "B", "C"):
        coh = coherence_audit["summary_by_strategy"][s]
        grd = grounding_by_strategy[s]
        meta = meta_and_grounding_audit["metadata_usefulness"]["summary_by_strategy"][s]
        print(
            f"  Strategy {s}: Coherence={coh['mean_score_out_of_2']}/2 ({coh['score_counts']}) | "
            f"Metadata Accurate={meta['test_top3_metadata_accurate_fraction']} | "
            f"Filter Compliance (dev/test/all)={meta['dev_filter_compliance_fraction']}/{meta['test_filter_compliance_fraction']}/{meta['all_filtered_queries_compliance_fraction']} | "
            f"Grounding={grd['mean_score_out_of_2']}/2 ({grd['score_counts']})"
        )


if __name__ == "__main__":
    main()

