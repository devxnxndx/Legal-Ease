"""
PDF processing pipeline.

1. extract_pdf_pages  — pull text from every page using pypdf
2. chunk_page_text    — split long pages into overlapping chunks
3. process_pdf        — convenience wrapper (bytes → chunks + page count)
"""
from __future__ import annotations

import io
from pypdf import PdfReader

# ---------------------------------------------------------------------------
# Tuning constants
# ---------------------------------------------------------------------------
CHUNK_SIZE = 1000       # characters per chunk (≈ 400-500 tokens)
CHUNK_OVERLAP = 20   # overlap to preserve cross-boundary context


# ---------------------------------------------------------------------------
# Step 1 — extract raw text per page
# ---------------------------------------------------------------------------
def extract_pdf_pages(pdf_bytes: bytes) -> tuple[list[dict], int]:
    """
    Parse a PDF from raw bytes.

    Returns:
        pages      — list of {"page": int, "text": str} (1-indexed, skips blank pages)
        page_count — total number of pages in the PDF
    """
    reader = PdfReader(io.BytesIO(pdf_bytes))
    page_count = len(reader.pages)
    pages: list[dict] = []

    for i, page in enumerate(reader.pages):
        raw = page.extract_text() or ""
        # Collapse whitespace runs for cleaner chunks
        text = " ".join(raw.split()).strip()
        if text:
            pages.append({"page": i + 1, "text": text})

    print(f"[pdf_processor] Pages with text: {len(pages)} / {page_count}")
    if pages:
        print(f"[pdf_processor] First 200 chars: {pages[0]['text'][:200]}")

    return pages, page_count


# ---------------------------------------------------------------------------
# Step 2 — sliding-window chunking
# ---------------------------------------------------------------------------
def chunk_page_text(pages: list[dict]) -> list[dict]:
    """
    Split each page's text into overlapping chunks.

    Returns a list of:
        {"content": str, "pageNumber": int, "chunkIndex": int}
    """
    chunks: list[dict] = []
    chunk_index = 0

    for page_data in pages:
        page_num = page_data["page"]
        text = page_data["text"]

        if not text.strip():
            continue

        if len(text) <= CHUNK_SIZE:
            # Entire page fits in one chunk
            chunks.append({
                "content": text,
                "pageNumber": page_num,
                "chunkIndex": chunk_index,
            })
            chunk_index += 1
        else:
            # Slide a window across the page text
            start = 0
            while start < len(text):
                end = min(start + CHUNK_SIZE, len(text))
                content = text[start:end].strip()
                if content:
                    chunks.append({
                        "content": content,
                        "pageNumber": page_num,
                        "chunkIndex": chunk_index,
                    })
                    chunk_index += 1
                start += CHUNK_SIZE - CHUNK_OVERLAP

    print(f"[pdf_processor] Total chunks: {len(chunks)}")
    return chunks


# ---------------------------------------------------------------------------
# Step 3 — convenience wrapper
# ---------------------------------------------------------------------------
def process_pdf(pdf_bytes: bytes) -> tuple[list[dict], int]:
    """
    Full pipeline: raw PDF bytes → (chunks, page_count).

    Raises ValueError if no text could be extracted (e.g. scanned image PDF).
    """
    pages, page_count = extract_pdf_pages(pdf_bytes)
    chunks = chunk_page_text(pages)
    return chunks, page_count
