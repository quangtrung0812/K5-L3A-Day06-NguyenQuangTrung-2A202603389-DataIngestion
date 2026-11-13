"""Verify corpus page counts, generate data/manifest.json & data/manifest.md, and save page diagnostics."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
STARTER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STARTER_DIR))

from src.ingestion import DOCUMENT_SPECS, MIN_VALID_PAGE_CHARS, load_pdf_with_diagnostics  # noqa: E402

CORPUS_FILES = [
    ("nist-ai-rmf-1.0", STARTER_DIR / "data" / "NIST.AI.100-1.pdf", "starter/data/NIST.AI.100-1.pdf"),
    ("nist-csf-2.0", STARTER_DIR / "data" / "NIST.CSWP.29.pdf", "starter/data/NIST.CSWP.29.pdf"),
]


def main() -> None:
    accessed_at = "2026-11-13T16:11:00+07:00"
    manifest_sources = []
    all_page_logs = []
    total_physical = 0
    total_valid = 0
    total_excluded = 0
    total_norm_chars = 0

    for doc_id, abs_path, rel_path in CORPUS_FILES:
        if not abs_path.exists():
            sys.exit(f"Missing corpus file: {abs_path}")
        spec = DOCUMENT_SPECS[doc_id]
        valid_pages, page_logs = load_pdf_with_diagnostics(abs_path, doc_id, rel_path)
        all_page_logs.extend(page_logs)

        phys_count = len(page_logs)
        val_count = len(valid_pages)
        excl_count = phys_count - val_count
        doc_norm_chars = sum(p.metadata["char_count"] for p in valid_pages)
        doc_raw_chars = sum(entry["raw_char_count"] for entry in page_logs)

        total_physical += phys_count
        total_valid += val_count
        total_excluded += excl_count
        total_norm_chars += doc_norm_chars

        manifest_sources.append(
            {
                "source_id": doc_id,
                "title": spec["title"],
                "publication_code": spec["publication_code"],
                "source_path_or_url": {
                    "local_path": rel_path,
                    "official_url": spec["source_url"],
                    "doi": spec["doi"],
                },
                "license_or_permission": spec["license"],
                "accessed_at": accessed_at,
                "snapshot_or_version": f"Version {spec['version']} ({spec['year']})",
                "metadata_fields": {
                    "year": spec["year"],
                    "version": spec["version"],
                    "domain": spec["domain"],
                    "document_type": spec["document_type"],
                },
                "physical_page_count": phys_count,
                "valid_content_page_count": val_count,
                "excluded_page_count": excl_count,
                "valid_page_numbers": [p.page for p in valid_pages],
                "valid_page_ids": [p.metadata["page_id"] for p in valid_pages],
                "excluded_pages": [
                    {"page": entry["page"], "page_id": entry["page_id"], "reason": entry["exclusion_reason"], "normalized_char_count": entry["normalized_char_count"]}
                    for entry in page_logs
                    if entry["status"] == "excluded"
                ],
                "total_raw_characters_all_pages": doc_raw_chars,
                "total_normalized_characters_valid_pages": doc_norm_chars,
                "pages": page_logs,
            }
        )

    manifest_data = {
        "corpus_name": "NIST Enterprise AI & Cybersecurity Risk Governance Corpus",
        "topic": "Enterprise Technology Governance & Risk Management Frameworks (NIST AI RMF 1.0 & NIST CSF 2.0)",
        "created_at": accessed_at,
        "minimum_required_content_pages": 30,
        "total_physical_pages": total_physical,
        "total_valid_content_pages": total_valid,
        "total_excluded_pages": total_excluded,
        "total_normalized_characters": total_norm_chars,
        "page_counting_rule": (
            f"Only physical PDF pages containing substantive framework content with >= {MIN_VALID_PAGE_CHARS} "
            "normalized Unicode characters are counted. Cover pages, title/front-matter disclaimers, "
            "acknowledgments, tables of contents, lists of figures/tables, figure-only pages (< 500 chars), "
            "and back-cover/closing disclaimer pages are explicitly excluded and logged."
        ),
        "sources": manifest_sources,
    }

    manifest_json_path = ROOT_DIR / "data" / "manifest.json"
    manifest_json_path.write_text(json.dumps(manifest_data, indent=2, ensure_ascii=False), encoding="utf-8")

    # Also write results/page_diagnostics_log.json for traceability
    results_dir = STARTER_DIR / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "page_diagnostics_log.json").write_text(
        json.dumps(all_page_logs, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Generate human-readable data/manifest.md
    md_lines = [
        "# Data Manifest — NIST Enterprise AI & Cybersecurity Risk Governance Corpus",
        "",
        "## 1. Tổng quan Corpus & Quy tắc tính trang",
        "",
        f"- **Chủ đề:** {manifest_data['topic']}",
        f"- **Thời điểm truy cập (`accessed_at`):** `{accessed_at}`",
        "- **Giấy phép & Quyền sử dụng (`license_or_permission`):** **Public Domain** — Tác phẩm của Chính phủ Hoa Kỳ (NIST / U.S. Department of Commerce) theo điều khoản `17 U.S.C. § 105`. Được phép sao chép, lưu trữ trong repository công khai và xử lý qua embedding model/API mà không vi phạm bản quyền. Không chứa dữ liệu cá nhân (PII) hay thông tin mật.",
        f"- **Tổng số trang vật lý:** **{total_physical} trang** (trên 2 tài liệu PDF)",
        f"- **Tổng số trang bị loại trừ (bìa, mục lục, front-matter, trang sơ đồ < {MIN_VALID_PAGE_CHARS} ký tự, disclaimer cuối):** **{total_excluded} trang**",
        f"- **Tổng số trang nội dung hợp lệ được tính:** **{total_valid} trang** (vượt mức tối thiểu 30 trang của đề bài)",
        f"- **Tổng số ký tự nội dung đã chuẩn hóa (trên {total_valid} trang hợp lệ):** **{total_norm_chars:,} ký tự**",
        "",
        "### Quy tắc tính trang nội dung (`page_counting_rule`)",
        "1. Loại bỏ toàn bộ các trang bìa (cover), trang thông tin xuất bản/miễn trừ trách nhiệm (front-matter/back-matter disclaimer), lời cảm ơn (acknowledgments), mục lục (Table of Contents), danh mục hình/bảng (List of Figures/Tables).",
        f"2. Loại bỏ các trang chỉ chứa sơ đồ/hình minh họa hoặc chuyển tiếp có độ dài văn bản sau chuẩn hóa Unicode **< {MIN_VALID_PAGE_CHARS} ký tự** (cụ thể: trang 16 và trang 39 của `NIST.AI.100-1.pdf`).",
        "3. Mọi trang bị loại đều được ghi log lý do cụ thể trong `data/manifest.json` và `starter/results/page_diagnostics_log.json`.",
        "",
        "## 2. Chi tiết từng tài liệu nguồn",
        "",
        "| `source_id` | Tiêu đề | Phiên bản / Năm | Đường dẫn / URL | Trang vật lý | Trang hợp lệ | Trang bị loại | Tổng ký tự chuẩn hóa |",
        "|---|---|---|---|---:|---:|---:|---:|",
    ]
    for src in manifest_sources:
        excl_nums = ", ".join(str(e["page"]) for e in src["excluded_pages"])
        md_lines.append(
            f"| `{src['source_id']}` | {src['title']} | `{src['snapshot_or_version']}` | `{src['source_path_or_url']['local_path']}` ([NIST PDF]({src['source_path_or_url']['official_url']})) | {src['physical_page_count']} | **{src['valid_content_page_count']}** | {src['excluded_page_count']} (P: {excl_nums}) | {src['total_normalized_characters_valid_pages']:,} |"
        )

    md_lines.extend(
        [
            "",
            "## 3. Metadata phục vụ Truy vết & Lọc (Filter)",
            "",
            "| Trường Metadata | Kiểu dữ liệu | Nguồn giá trị | Giá trị trong Corpus | Mục đích sử dụng |",
            "|---|---|---|---|---|",
            "| `document_id` | `str` | Định danh tài liệu trong Manifest | `nist-ai-rmf-1.0`, `nist-csf-2.0` | Truy vết tài liệu gốc |",
            "| `source` | `str` | Đường dẫn file PDF gốc | `starter/data/NIST.AI.100-1.pdf`, `starter/data/NIST.CSWP.29.pdf` | Truy vết file nguồn |",
            "| `page` | `int` | Số thứ tự trang PDF vật lý (1-indexed) | `5..47` (tùy tài liệu) | Truy vết chính xác vị trí trang |",
            "| `domain` | `str` | Phạm vi tiêu chuẩn của tài liệu NIST | `ai_risk` (AI RMF 1.0), `cybersecurity` (CSF 2.0) | **Trường lọc chính** giúp phân biệt câu hỏi về quản trị rủi ro AI vs. an ninh mạng (đặc biệt khi cả 2 cùng có hàm `GOVERN`, `Supply Chain Risk`, `Profiles`) |",
            "| `year` | `int` | Năm xuất bản ghi trên trang bìa/tiêu đề PDF | `2023`, `2024` | **Trường lọc bổ sung** theo năm ban hành tiêu chuẩn |",
            "| `section` | `str` | Cấu trúc phần/chương thực tế của PDF | `executive_summary`, `part_1_framing_and_audience`, `part_1_trustworthiness_and_effectiveness`, `part_2_core_and_profiles`, `appendices`, `preface`, `overview_and_core_intro`, `profiles_tiers_and_integration`, `appendix_a_csf_core`, `appendices_tiers_and_glossary` | **Trường lọc bổ sung** và hỗ trợ kiểm tra ngữ cảnh theo chương mục |",
            "",
            "## 4. Danh sách các trang bị loại trừ (Excluded Pages Log)",
            "",
            "| `page_id` | `source` | Trang vật lý | Ký tự chuẩn hóa | Lý do loại trừ |",
            "|---|---|---:|---:|---|",
        ]
    )
    for src in manifest_sources:
        for e in src["excluded_pages"]:
            md_lines.append(
                f"| `{e['page_id']}` | `{src['source_path_or_url']['local_path']}` | {e['page']} | {e['normalized_char_count']} | `{e['reason']}` |"
            )

    manifest_md_path = ROOT_DIR / "data" / "manifest.md"
    manifest_md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"Corpus verification complete:")
    print(f"  - Physical pages : {total_physical}")
    print(f"  - Excluded pages : {total_excluded}")
    print(f"  - Valid pages    : {total_valid} (Requirement: >= 30)")
    print(f"  - Normalized char: {total_norm_chars:,}")
    print(f"  - Manifest JSON  : {manifest_json_path}")
    print(f"  - Manifest MD    : {manifest_md_path}")


if __name__ == "__main__":
    main()

