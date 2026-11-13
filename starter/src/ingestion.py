"""Read and normalize source data for the NIST Governance & Risk Corpus."""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from .models import DocumentPage

MIN_VALID_PAGE_CHARS = 500

# Explicit, source-verified page rules and section mappings per document_id
DOCUMENT_SPECS: dict[str, dict[str, Any]] = {
    "nist-ai-rmf-1.0": {
        "title": "Artificial Intelligence Risk Management Framework (AI RMF 1.0)",
        "year": 2023,
        "version": "1.0",
        "domain": "ai_risk",
        "document_type": "framework",
        "publication_code": "NIST AI 100-1",
        "source_url": "https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf",
        "doi": "https://doi.org/10.6028/NIST.AI.100-1",
        "license": "Public Domain (U.S. Government Work, 17 U.S.C. § 105)",
        "excluded_pages": {
            1: "cover_page",
            2: "front_matter_publication_info",
            3: "front_matter_disclaimer_and_version_schedule",
            4: "table_of_contents",
            5: "list_of_figures_and_tables",
            16: "low_text_figure_only (Fig. 3, <500 chars)",
            39: "low_text_transition_page (<500 chars)",
            48: "back_cover_doi_only",
        },
        "section_ranges": [
            (6, 8, "executive_summary"),
            (9, 15, "part_1_framing_and_audience"),
            (17, 24, "part_1_trustworthiness_and_effectiveness"),
            (25, 38, "part_2_core_and_profiles"),
            (40, 47, "appendices"),
        ],
    },
    "nist-csf-2.0": {
        "title": "The NIST Cybersecurity Framework (CSF) 2.0",
        "year": 2024,
        "version": "2.0",
        "domain": "cybersecurity",
        "document_type": "framework",
        "publication_code": "NIST CSWP 29",
        "source_url": "https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf",
        "doi": "https://doi.org/10.6028/NIST.CSWP.29",
        "license": "Public Domain (U.S. Government Work, 17 U.S.C. § 105)",
        "excluded_pages": {
            1: "cover_page",
            2: "front_matter_abstract",
            3: "front_matter_acknowledgments",
            4: "table_of_contents_and_figures",
            32: "back_matter_disclaimer_and_notes",
        },
        "section_ranges": [
            (5, 5, "preface"),
            (6, 10, "overview_and_core_intro"),
            (11, 19, "profiles_tiers_and_integration"),
            (20, 28, "appendix_a_csf_core"),
            (29, 31, "appendices_tiers_and_glossary"),
        ],
    },
}


def normalize_text(text: str) -> str:
    """Normalize Unicode (NFC) and whitespace while preserving paragraph structure."""
    if not text:
        return ""
    norm = unicodedata.normalize("NFC", text)
    norm = norm.replace("\r\n", "\n").replace("\r", "\n")
    # Remove recurring running headers at top of pages to improve chunk coherence
    norm = re.sub(
        r"(?m)^NIST AI 100-1\s+AI RMF 1\.0\s*$",
        "",
        norm,
    )
    norm = re.sub(
        r"(?m)^NIST CSWP 29\s+The NIST Cybersecurity Framework \(CSF\) 2\.0\s*\nFebruary 26, 2024\s*\n(?:\d+|[ivx]+)\s*$",
        "",
        norm,
    )
    # Rejoin hyphenated words broken across lines (e.g. "organi-\nzations" -> "organizations")
    norm = re.sub(r"([A-Za-z])-\s*\n\s*([a-z])", r"\1\2", norm)
    # Clean horizontal spaces per line
    cleaned_lines = [re.sub(r"[ \t]+", " ", line).strip() for line in norm.split("\n")]
    # Reconstruct paragraphs: join single line wraps within a paragraph, keep blank lines/headings/bullets separate
    rebuilt: list[str] = []
    for line in cleaned_lines:
        if not line:
            if rebuilt and rebuilt[-1] != "":
                rebuilt.append("")
            continue
        is_heading_or_bullet = bool(
            re.match(
                r"^(?:Part \d+|Appendix [A-Z]|Table \d+|Fig\.\s*\d+|\d+(?:\.\d+)*\s+[A-Z]|[•◦o▪\-]\s+|[A-Z]{2,}(?:\.[A-Z]{2,})?(?:-\d+)?\s*:)",
                line,
            )
        )
        if not rebuilt or rebuilt[-1] == "" or is_heading_or_bullet:
            rebuilt.append(line)
        else:
            prev = rebuilt[-1]
            if prev.endswith((".", ":", ";", "?", "!")):
                rebuilt.append(line)
            else:
                rebuilt[-1] = f"{prev} {line}"
    result = "\n\n".join(p for p in rebuilt if p != "")
    return result.strip()


def _resolve_section(document_id: str, page_num: int) -> str:
    spec = DOCUMENT_SPECS.get(document_id, {})
    for start_p, end_p, sec_name in spec.get("section_ranges", []):
        if start_p <= page_num <= end_p:
            return sec_name
    return "general"


def load_pdf_with_diagnostics(
    path: Path, document_id: str, source: str
) -> tuple[list[DocumentPage], list[dict[str, Any]]]:
    """Extract physical pages, separate valid content pages from excluded/empty pages, and log diagnostics."""
    reader = PdfReader(str(path))
    spec = DOCUMENT_SPECS.get(document_id, {})
    excluded_map: dict[int, str] = spec.get("excluded_pages", {})

    valid_pages: list[DocumentPage] = []
    page_logs: list[dict[str, Any]] = []

    for page_num, pdf_page in enumerate(reader.pages, start=1):
        raw_text = pdf_page.extract_text() or ""
        norm_text = normalize_text(raw_text)
        raw_chars = len(raw_text.strip())
        norm_chars = len(norm_text)

        exclusion_reason = excluded_map.get(page_num)
        if exclusion_reason is None and norm_chars == 0:
            exclusion_reason = "empty_unextractable_page"
        elif exclusion_reason is None and norm_chars < MIN_VALID_PAGE_CHARS:
            exclusion_reason = f"below_min_char_threshold ({norm_chars} < {MIN_VALID_PAGE_CHARS})"

        is_valid = exclusion_reason is None
        section = _resolve_section(document_id, page_num) if is_valid else "excluded"

        log_entry = {
            "page_id": f"{document_id}:p{page_num:02d}",
            "document_id": document_id,
            "source": source,
            "page": page_num,
            "raw_char_count": raw_chars,
            "normalized_char_count": norm_chars,
            "status": "valid" if is_valid else "excluded",
            "exclusion_reason": exclusion_reason,
            "section": section,
        }
        page_logs.append(log_entry)

        if is_valid:
            metadata = {
                "page_id": f"{document_id}:p{page_num:02d}",
                "year": spec.get("year"),
                "version": spec.get("version"),
                "domain": spec.get("domain"),
                "document_type": spec.get("document_type", "framework"),
                "section": section,
                "char_count": norm_chars,
            }
            valid_pages.append(
                DocumentPage(
                    document_id=document_id,
                    source=source,
                    page=page_num,
                    text=norm_text,
                    metadata=metadata,
                )
            )

    return valid_pages, page_logs


def load_pdf(path: Path, document_id: str, source: str) -> list[DocumentPage]:
    """Extract each valid content page; keep its physical page number, source, and metadata."""
    valid_pages, _ = load_pdf_with_diagnostics(path, document_id, source)
    return valid_pages
