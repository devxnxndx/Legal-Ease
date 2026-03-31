"""
Chat router

POST /api/cases/{case_id}/chat  — send a message; returns an SSE stream
GET  /api/cases/{case_id}/chat  — fetch chat history for a case
"""
import json
import time
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from lib.supabase_client import get_supabase
from lib.gemini import stream_chat_with_context
from lib.rag import retrieve_context
from lib.runtime_priority import chat_started, chat_ping, chat_finished

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = Field(default_factory=list)


@router.post("/cases/{case_id}/chat")
async def chat(case_id: str, body: ChatRequest):
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    supabase = get_supabase()

    case_result = (
        supabase.from_("cases")
        .select("id, status")
        .eq("id", case_id)
        .single()
        .execute()
    )

    if not case_result.data:
        raise HTTPException(status_code=404, detail="Case not found.")

    if case_result.data["status"] != "ready":
        raise HTTPException(status_code=409, detail="Case is still processing; please wait.")

    supabase.from_("chat_messages").insert({
        "case_id": case_id,
        "role": "user",
        "content": body.message,
    }).execute()

    async def event_stream():
        full_response = ""
        sources = []

        chat_started()
        try:
            yield f"data: {json.dumps({'type': 'status', 'message': 'Searching documents...'})}\n\n"

            t1 = time.perf_counter()
            rag_result = await retrieve_context(body.message, case_id)
            print(f"[chat] RAG took {(time.perf_counter() - t1) * 1000:.0f} ms")
            chat_ping()

            context = rag_result["context"]
            sources = rag_result["sources"]

            yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
            yield f"data: {json.dumps({'type': 'status', 'message': 'Generating answer...'})}\n\n"

            first_token = True
            t2 = time.perf_counter()
            
            # --- Anti-Legal-Advice Fallback Net ---
            bad_phrases = ["you should", "you must", "i recommend", "legal action"]
            is_replaced = False

            # We process chat tokens as they stream from the model
            async for token in stream_chat_with_context(body.message, context, body.history):
                if first_token:
                    print(f"[chat] Gemini first token: {(time.perf_counter() - t2) * 1000:.0f} ms")
                    first_token = False

                full_response += token
                
                # Check if response crossed the boundary into legal advice
                lower_resp = full_response.lower()
                if any(phrase in lower_resp for phrase in bad_phrases):
                    is_replaced = True
                    safe_message = "I can explain what the document says, but I cannot provide legal advice."
                    # Emit a replacement event to instruct the client to overwrite the message
                    yield f"data: {json.dumps({'type': 'replace', 'text': safe_message})}\n\n"
                    full_response = safe_message # Overwrite the saved content with the safe string
                    break # Stop processing tokens

                if not is_replaced:
                    chat_ping()
                    # Emit natural token event
                    yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"

            print(f"[chat] Gemini total: {(time.perf_counter() - t2) * 1000:.0f} ms")
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

            if full_response.strip():
                supabase.from_("chat_messages").insert({
                    "case_id": case_id,
                    "role": "ai",
                    "content": full_response,
                    "sources": sources if sources else None,
                }).execute()

        except Exception as e:
            print(f"[chat] Stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': 'Stream failed — please try again.'})}\n\n"
        finally:
            chat_finished()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/cases/{case_id}/chat")
async def get_messages(case_id: str):
    supabase = get_supabase()
    result = (
        supabase.from_("chat_messages")
        .select("*")
        .eq("case_id", case_id)
        .order("created_at")
        .execute()
    )
    if result.data is None:
        raise HTTPException(status_code=500, detail="Failed to fetch chat history.")
    return {"messages": result.data}

@router.get("/cases/{case_id}/faqs")
async def get_faqs(case_id: str):
    """
    Fetch the most common user queries for this case.
    """
    from collections import Counter
    supabase = get_supabase()
    result = (
        supabase.from_("chat_messages")
        .select("content")
        .eq("case_id", case_id)
        .eq("role", "user")
        .execute()
    )
    if not result.data:
        return {"faqs": []}
        
    counts = Counter(row["content"].strip() for row in result.data if len(row["content"]) < 120)
    faqs = [q for q, _ in counts.most_common(3)]
    
    return {"faqs": faqs}