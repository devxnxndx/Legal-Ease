"""
Retrieval-Augmented Generation (RAG) helpers.

retrieve_context:
  1. Embed the user's query with Gemini text-embedding-001 (768-dim).
  2. Call the Supabase `match_document_chunks` RPC (pgvector cosine search).
  3. Fetch document names for readable citations.
  4. Return a formatted context string + a list of source dicts for the UI.
"""
from __future__ import annotations

import asyncio
from lib.gemini import embed_text
from lib.supabase_client import get_supabase


async def retrieve_context(
    query: str,
    case_id: str,
    threshold: float = 0.3,
    top_k: int = 5,
) -> dict:
    """
    Retrieve the top-k most relevant document chunks for *query* within
    the given *case_id*.

    Args:
        query      — the user's natural-language question
        case_id    — UUID of the case whose documents to search
        threshold  — minimum cosine similarity (0–1); lower = broader recall
        top_k      — maximum number of chunks to return

    Returns:
        {
            "context": str,         # formatted text to inject into Gemini prompt
            "sources": list[dict],  # [{chunk_id, page, snippet, document_name}]
        }
    """
    supabase = get_supabase()

    # ── 1. Embed the query ────────────────────────────────────────────────
    try:
        query_embedding = await asyncio.wait_for(embed_text(query), timeout=15.0)
    except asyncio.TimeoutError:
        print("[RAG] Embedding timed out — returning empty context")
        return {"context": "", "sources": []}

    # ── 2. Vector similarity search via Supabase RPC ──────────────────────
    result = supabase.rpc(
        "match_document_chunks",
        {
            "query_embedding": query_embedding,
            "match_case_id": case_id,
            "match_threshold": threshold,
            "match_count": top_k,
        },
    ).execute()

    chunks = result.data or []

    if not chunks:
        print("[RAG] No chunks matched — returning empty context")
        return {"context": "", "sources": []}

    # ── 3. Resolve document names for readable citations ──────────────────
    doc_ids = list({c["document_id"] for c in chunks})
    docs_result = (
        supabase.from_("documents")
        .select("id, name")
        .in_("id", doc_ids)
        .execute()
    )
    doc_name_map: dict[str, str] = {
        d["id"]: d["name"] for d in (docs_result.data or [])
    }

    # ── 4. Build context string (injected into Gemini prompt) ─────────────
    context_parts = [
        f"[{doc_name_map.get(c['document_id'], 'Document')} — Page {c['page_number']}]\n"
        f"{c['content'][:800]}"
        for c in chunks
    ]
    context = "\n\n---\n\n".join(context_parts)

    # ── 5. Build source list (returned to frontend for citations) ─────────
    sources = [
        {
            "chunk_id": c["id"],
            "page": c["page_number"],
            "snippet": c["content"][:120] + ("…" if len(c["content"]) > 120 else ""),
            "document_name": doc_name_map.get(c["document_id"]),
        }
        for c in chunks
    ]

    print(f"[RAG] Returning {len(chunks)} chunks for query: {query[:60]}…")
    return {"context": context, "sources": sources}
