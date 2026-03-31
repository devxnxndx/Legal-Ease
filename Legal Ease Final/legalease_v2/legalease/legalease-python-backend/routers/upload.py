"""
Upload router

POST /api/cases/upload       — create a new case + upload its first PDF
POST /api/cases/upload-doc   — add a second (or Nth) PDF to an existing case
"""
import time
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, BackgroundTasks
import asyncio
from lib.supabase_client import get_supabase
from lib.pdf_processor import process_pdf
from lib.gemini import embed_batch, generate_summary, score_contract_risk, detect_clauses, extract_deadlines

router = APIRouter()

# Gemini's embed_content API accepts batches; we chunk to avoid rate limits.
_EMBED_BATCH_SIZE = 50


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_pdf(file: UploadFile, pdf_bytes: bytes) -> None:
    """Raise HTTPException for invalid uploads."""
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")
    if len(pdf_bytes) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File must be under 50 MB.")

async def _analyze_document_background(case_id: str, doc_id: str, chunks_text: str):
    """Run heavy LLM analysis in the background."""
    supabase = get_supabase()
    print(f"[upload] Starting background analysis for case {case_id}")
    try:
        # Run sequentially with slight delays to respect Gemini free-tier RPM/TPM limits
        try:
            summary = await generate_summary(chunks_text)
            await asyncio.sleep(2)
        except Exception as e:
            summary = ""
            print(f"Summary error: {e}")

        try:
            risk_data = await score_contract_risk(chunks_text)
            await asyncio.sleep(2)
        except Exception as e:
            risk_data = {}
            print(f"Risk error: {e}")

        try:
            clauses_data = await detect_clauses(chunks_text)
            await asyncio.sleep(2)
        except Exception as e:
            clauses_data = []
            print(f"Clause error: {e}")

        try:
            deadlines_data = await extract_deadlines(chunks_text)
        except Exception as e:
            deadlines_data = []
            print(f"Deadline error: {e}")

        # Update case
        updates = {"status": "ready"}
        if summary:
            updates["summary"] = summary
        if isinstance(risk_data, dict) and "score" in risk_data:
            updates["risk_score"] = risk_data.get("score")
            updates["risk_explanation"] = risk_data.get("explanation")
        
        supabase.from_("cases").update(updates).eq("id", case_id).execute()

        # Insert clauses
        if isinstance(clauses_data, list) and clauses_data:
            clause_rows = []
            for c in clauses_data:
                clause_rows.append({
                    "case_id": case_id,
                    "document_id": doc_id,
                    "tag_type": c.get("type", "unknown"),
                    "excerpt": c.get("excerpt", ""),
                    "page_number": c.get("page", 1)
                })
            if clause_rows:
                supabase.from_("document_tags").insert(clause_rows).execute()
        
        # Insert deadlines
        if isinstance(deadlines_data, list) and deadlines_data:
            deadline_rows = []
            for d in deadlines_data:
                deadline_rows.append({
                    "case_id": case_id,
                    "document_id": doc_id,
                    "deadline_date": d.get("date", ""),
                    "event": d.get("event", ""),
                    "description": d.get("description", ""),
                    "page_number": d.get("page", 1)
                })
            if deadline_rows:
                supabase.from_("deadlines").insert(deadline_rows).execute()
                
        print(f"[upload] Finished background analysis for case {case_id}")
            
    except Exception as e:
        print(f"[upload] Background analysis failed: {e}")
        supabase.from_("cases").update({"status": "ready"}).eq("id", case_id).execute()


async def _process_and_index(
    supabase,
    pdf_bytes: bytes,
    filename: str,
    case_id: str,
) -> dict:
    """
    Shared logic for both upload endpoints:
      1. Upload raw bytes to Supabase Storage.
      2. Extract + chunk PDF text.
      3. Embed chunks in batches.
      4. Insert document + chunk rows into Supabase.

    Returns a dict with documentId, pageCount, chunkCount, chunks (raw text).
    """
    safe_name = filename.replace(" ", "_")
    storage_path = f"{case_id}/{int(time.time())}-{safe_name}"

    supabase.storage.from_("legal-documents").upload(
        storage_path,
        pdf_bytes,
        {"content-type": "application/pdf"},
    )

    chunks, page_count = process_pdf(pdf_bytes)
    print(f"[upload] Extracted {len(chunks)} chunks from '{filename}'")

    if not chunks:
        raise HTTPException(
            status_code=422,
            detail="Could not extract text from the PDF. Is it a scanned image?",
        )

    display_name = (
        filename
        .removesuffix(".pdf")
        .removesuffix(".PDF")
        .replace("_", " ")
    )

    doc_result = (
        supabase.from_("documents")
        .insert({
            "case_id": case_id,
            "name": display_name,
            "storage_path": storage_path,
            "page_count": page_count,
        })
        .execute()
    )

    if doc_result.data:
        doc_id = doc_result.data[0]["id"]
    else:
        lookup = (
            supabase.from_("documents")
            .select("id")
            .eq("storage_path", storage_path)
            .single()
            .execute()
        )
        if not lookup.data:
            raise HTTPException(status_code=500, detail="Failed to create document record.")
        doc_id = lookup.data["id"]

    all_embeddings: list[list[float]] = []
    for i in range(0, len(chunks), _EMBED_BATCH_SIZE):
        batch = chunks[i:i + _EMBED_BATCH_SIZE]
        embeddings = await embed_batch([c["content"] for c in batch])
        all_embeddings.extend(embeddings)

    print(
        f"[upload] Generated {len(all_embeddings)} embeddings "
        f"(dim={len(all_embeddings[0]) if all_embeddings else 0})"
    )

    chunk_rows = [
        {
            "document_id": doc_id,
            "case_id": case_id,
            "content": chunks[i]["content"],
            "page_number": chunks[i]["pageNumber"],
            "chunk_index": chunks[i]["chunkIndex"],
            "embedding": all_embeddings[i],
        }
        for i in range(len(chunks))
    ]

    insert_result = supabase.from_("document_chunks").insert(chunk_rows).execute()
    print(f"[upload] Inserted {len(insert_result.data or [])} chunk rows")

    return {
        "documentId": doc_id,
        "pageCount": page_count,
        "chunkCount": len(chunks),
        "chunks": chunks,
    }


# ---------------------------------------------------------------------------
# POST /api/cases/upload  — create case + first document
# ---------------------------------------------------------------------------
@router.post("/cases/upload")
async def upload_case(
    title: str = Form(...),
    file: UploadFile = File(...),
):
    """
    Create a new case and process its first PDF document.
    Returns { caseId, documentId, pageCount, chunkCount }.
    """
    if not title.strip():
        raise HTTPException(status_code=400, detail="Case title is required.")

    pdf_bytes = await file.read()
    _validate_pdf(file, pdf_bytes)

    supabase = get_supabase()

    case_result = (
        supabase.from_("cases")
        .insert({"title": title.strip(), "status": "processing"})
        .execute()
    )

    if case_result.data:
        case_id = case_result.data[0]["id"]
    else:
        lookup = (
            supabase.from_("cases")
            .select("id")
            .eq("title", title.strip())
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if not lookup.data:
            raise HTTPException(status_code=500, detail="Failed to create case record.")
        case_id = lookup.data[0]["id"]

    try:
        doc_info = await _process_and_index(
            supabase, pdf_bytes, file.filename or "document.pdf", case_id
        )

        # Trigger background analysis
        chunks_text = "\n\n".join([c["content"] for c in doc_info["chunks"]])
        asyncio.create_task(_analyze_document_background(case_id, doc_info["documentId"], chunks_text))

        return {
            "caseId": case_id,
            "documentId": doc_info["documentId"],
            "pageCount": doc_info["pageCount"],
            "chunkCount": doc_info["chunkCount"],
        }

    except HTTPException:
        supabase.from_("cases").update({"status": "error"}).eq("id", case_id).execute()
        raise
    except Exception as e:
        print(f"[upload] Unexpected error: {e}")
        supabase.from_("cases").update({"status": "error"}).eq("id", case_id).execute()
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# POST /api/cases/upload-doc  — add a document to an existing case
# ---------------------------------------------------------------------------
@router.post("/cases/upload-doc")
async def upload_document(
    caseId: str = Form(...),
    file: UploadFile = File(...),
):
    """
    Add an additional PDF to an existing case.
    Returns { documentId, pageCount, chunkCount }.
    """
    pdf_bytes = await file.read()
    _validate_pdf(file, pdf_bytes)

    supabase = get_supabase()

    case_result = (
        supabase.from_("cases")
        .select("id, status")
        .eq("id", caseId)
        .single()
        .execute()
    )
    if not case_result.data:
        raise HTTPException(status_code=404, detail="Case not found.")

    try:
        # Set to processing again while second doc is analyzed
        supabase.from_("cases").update({"status": "processing"}).eq("id", caseId).execute()
        doc_info = await _process_and_index(
            supabase, pdf_bytes, file.filename or "document.pdf", caseId
        )
        
        # Trigger background analysis for the new doc
        chunks_text = "\n\n".join([c["content"] for c in doc_info["chunks"]])
        asyncio.create_task(_analyze_document_background(caseId, doc_info["documentId"], chunks_text))

        return {
            "documentId": doc_info["documentId"],
            "pageCount": doc_info["pageCount"],
            "chunkCount": doc_info["chunkCount"],
        }
    except HTTPException:
        supabase.from_("cases").update({"status": "ready"}).eq("id", caseId).execute()
        raise
    except Exception as e:
        print(f"[upload-doc] Unexpected error: {e}")
        supabase.from_("cases").update({"status": "ready"}).eq("id", caseId).execute()
        raise HTTPException(status_code=500, detail=str(e))