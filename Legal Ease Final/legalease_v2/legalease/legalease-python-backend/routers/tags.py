"""
Tags router

GET /api/cases/{case_id}/tags  — fetch all clause tags for a case
"""
from fastapi import APIRouter, HTTPException
from lib.supabase_client import get_supabase

router = APIRouter()


@router.get("/cases/{case_id}/tags")
async def get_tags(case_id: str):
    """Return all clause tags for a case, ordered by page number."""
    try:
        supabase = get_supabase()
        result = (
            supabase.from_("document_tags")
            .select("*")
            .eq("case_id", case_id)
            .order("page_number")
            .execute()
        )
        return {"tags": result.data or []}
    except Exception as e:
        print(f"[tags] get_tags error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch tags")
