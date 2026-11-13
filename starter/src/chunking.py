"""Implement fixed-size and structure-aware (paragraph/heading) chunking."""
from __future__ import annotations

import re
from .models import Chunk, DocumentPage


def _estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars per token or 1.3x words) for reporting."""
    words = len(text.split())
    return max(1, int(round(max(words * 1.3, len(text) / 4.0))))


def fixed_size(page: DocumentPage, size: int = 500, overlap: int = 50) -> list[Chunk]:
    """Split page text into overlapping fixed-size character windows and retain page metadata."""
    if size <= 0:
        raise ValueError("size must be > 0")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must satisfy 0 <= overlap < size")

    text = (page.text or "").strip()
    if not text:
        return []

    step = size - overlap
    chunks: list[Chunk] = []
    start = 0
    idx = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + size, text_len)
        window = text[start:end].strip()
        if window:
            idx += 1
            meta = dict(page.metadata)
            meta.update(
                {
                    "chunking_method": "fixed_size",
                    "chunk_size_param": size,
                    "overlap_param": overlap,
                    "chunk_index": idx,
                    "char_start": start,
                    "char_end": end,
                    "char_length": len(window),
                    "est_tokens": _estimate_tokens(window),
                }
            )
            chunks.append(
                Chunk(
                    chunk_id=f"{page.document_id}:p{page.page:02d}:fixed:{idx:03d}",
                    document_id=page.document_id,
                    source=page.source,
                    page=page.page,
                    text=window,
                    metadata=meta,
                )
            )
        if end >= text_len:
            break
        start += step

    return chunks


def _split_oversized_paragraph(paragraph: str, max_size: int) -> list[str]:
    """Split a paragraph larger than max_size along sentence boundaries first, then fallback to char slices."""
    if len(paragraph) <= max_size:
        return [paragraph]

    sentences = re.split(r"(?<=[.!?])\s+", paragraph)
    pieces: list[str] = []
    current = ""

    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        if len(sent) > max_size:
            if current:
                pieces.append(current)
                current = ""
            # Hard split on word boundaries if a single sentence exceeds max_size
            words = sent.split(" ")
            buf = ""
            for w in words:
                cand = f"{buf} {w}".strip() if buf else w
                if len(cand) <= max_size:
                    buf = cand
                else:
                    if buf:
                        pieces.append(buf)
                    buf = w[:max_size]
            if buf:
                pieces.append(buf)
        else:
            candidate = f"{current} {sent}".strip() if current else sent
            if len(candidate) <= max_size:
                current = candidate
            else:
                if current:
                    pieces.append(current)
                current = sent

    if current:
        pieces.append(current)
    return pieces


def by_paragraph(page: DocumentPage, max_size: int = 900) -> list[Chunk]:
    """Group structural paragraphs and headings up to max_size, split oversized paragraphs, and retain metadata."""
    if max_size <= 0:
        raise ValueError("max_size must be > 0")

    text = (page.text or "").strip()
    if not text:
        return []

    raw_paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    # Ensure oversized paragraphs are split cleanly at sentence boundaries
    units: list[str] = []
    for para in raw_paragraphs:
        units.extend(_split_oversized_paragraph(para, max_size))

    grouped_texts: list[str] = []
    current_group: list[str] = []
    current_len = 0

    for unit in units:
        sep_len = 2 if current_group else 0
        if current_group and (current_len + sep_len + len(unit) > max_size):
            grouped_texts.append("\n\n".join(current_group))
            current_group = [unit]
            current_len = len(unit)
        else:
            current_group.append(unit)
            current_len += sep_len + len(unit)

    if current_group:
        grouped_texts.append("\n\n".join(current_group))

    chunks: list[Chunk] = []
    for idx, chunk_text in enumerate(grouped_texts, start=1):
        meta = dict(page.metadata)
        meta.update(
            {
                "chunking_method": "by_paragraph",
                "max_size_param": max_size,
                "chunk_index": idx,
                "char_length": len(chunk_text),
                "est_tokens": _estimate_tokens(chunk_text),
            }
        )
        chunks.append(
            Chunk(
                chunk_id=f"{page.document_id}:p{page.page:02d}:para:{idx:03d}",
                document_id=page.document_id,
                source=page.source,
                page=page.page,
                text=chunk_text,
                metadata=meta,
            )
        )

    return chunks
