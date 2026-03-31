"""
PDF signed-URL router

GET /api/cases/{case_id}/pdf?documentId=<uuid>

Returns a short-lived (1 hour) signed URL so the frontend PDF viewer
can fetch the file directly from Supabase Storage without exposing the
service-role key.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from lib.supabase_client import get_supabase

router = APIRouter()


@router.get("/cases/{case_id}/pdf")
async def get_pdf_url(
    case_id: str,
    documentId: Optional[str] = Query(None),
):
    """
    Return a signed URL for the requested PDF document.

    If *documentId* is provided, fetch that specific document;
    otherwise fall back to the first document in the case.
    """
    supabase = get_supabase()

    query = (
        supabase.from_("documents")
        .select("storage_path, name")
        .eq("case_id", case_id)
    )
    if documentId:
        query = query.eq("id", documentId)

    result = query.limit(1).single().execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Document not found.")

    doc = result.data

    # Generate a signed URL valid for 1 hour (3600 seconds)
    signed = supabase.storage.from_("legal-documents").create_signed_url(
        doc["storage_path"], 3600
    )

    # Supabase Python SDK v2 uses 'signedUrl' (lowercase u);
    # v1 used 'signedURL'. Handle both to be safe.
    signed_url = (signed or {}).get("signedUrl") or (signed or {}).get("signedURL")

    if not signed_url:
        raise HTTPException(
            status_code=500,
            detail="Could not generate a signed URL for the document.",
        )

    return {"url": signed_url, "name": doc["name"]}
