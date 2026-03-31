from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import json
import math
from fastapi.responses import StreamingResponse
from lib.supabase_client import get_supabase
from lib.gemini import stream_chat_with_context, embed_text
import asyncio

router = APIRouter()

class GlobalSearchRequest(BaseModel):
    message: str
    history: list[dict] = Field(default_factory=list)

@router.post("/search/cross-case")
async def cross_case_search(body: GlobalSearchRequest):
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    supabase = get_supabase()

    async def event_stream():
        full_response = ""
        try:
            yield f"data: {json.dumps({'type': 'status', 'message': 'Searching all documents...'})}\n\n"

            # 1. Embed Query
            query_embedding = await asyncio.wait_for(embed_text(body.message), timeout=15.0)

            # 2. Fetch all document chunks globally
            # In a real app we'd paginate or use an RPC, but since match_document_chunks is pinned to a case_id, we pull manually.
            chunks_res = supabase.from_("document_chunks").select("id, content, page_number, document_id, embedding").execute()
            all_chunks = chunks_res.data or []
            
            # Simple Python-side cosine similarity
            def cosine_sim(a, b):
                dot = sum(x * y for x, y in zip(a, b))
                norm_a = math.sqrt(sum(x * x for x in a))
                norm_b = math.sqrt(sum(x * x for x in b))
                if norm_a == 0 or norm_b == 0: return 0.0
                return dot / (norm_a * norm_b)

            scored_chunks = []
            for c in all_chunks:
                if c.get("embedding"):
                    # We can use pure python since the DB should be small enough
                    score = cosine_sim(query_embedding, c["embedding"])
                    if score > 0.3:
                        scored_chunks.append((score, c))
            
            scored_chunks.sort(key=lambda x: x[0], reverse=True)
            top_chunks = [c for _, c in scored_chunks[:5]]
            
            if not top_chunks:
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return

            # Resolve document names
            doc_ids = list({c["document_id"] for c in top_chunks})
            docs_result = supabase.from_("documents").select("id, name, case_id").in_("id", doc_ids).execute()
            docs_data = docs_result.data or []
            doc_map = {d["id"]: d for d in docs_data}

            # Resolve case names
            case_ids = list({d["case_id"] for d in docs_data if d.get("case_id")})
            cases_result = supabase.from_("cases").select("id, title").in_("id", case_ids).execute()
            case_map = {c["id"]: c["title"] for c in (cases_result.data or [])}

            context_parts = []
            sources = []
            for c in top_chunks:
                doc = doc_map.get(c["document_id"], {})
                doc_name = doc.get("name", "Document")
                case_id = doc.get("case_id")
                case_title = case_map.get(case_id, "Unknown Case")
                
                context_parts.append(
                    f"[Case: {case_title} | Doc: {doc_name} | Page {c['page_number']}]\n"
                    f"{c['content'][:800]}"
                )
                
                sources.append({
                    "chunk_id": c["id"],
                    "page": c["page_number"],
                    "snippet": c["content"][:120] + "...",
                    "document_name": f"[{case_title}] {doc_name}",
                })

            context = "\n\n---\n\n".join(context_parts)

            yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
            yield f"data: {json.dumps({'type': 'status', 'message': 'Generating answer...'})}\n\n"

            # Re-use stream_chat_with_context to stream the final tokens
            async for token in stream_chat_with_context(body.message, context, body.history):
                full_response += token
                yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            print(f"[search] Stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': 'Search failed — please try again.'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
