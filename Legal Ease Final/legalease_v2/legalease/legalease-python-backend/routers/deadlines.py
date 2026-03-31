"""
Deadlines router

GET /api/cases/{case_id}/deadlines  — fetch all extracted deadlines for a case
"""
from fastapi import APIRouter, HTTPException
from lib.supabase_client import get_supabase

router = APIRouter()


@router.get("/cases/{case_id}/deadlines")
async def get_deadlines(case_id: str):
    """Return all deadlines for a case, ordered by page number."""
    try:
        supabase = get_supabase()
        result = (
            supabase.from_("deadlines")
            .select("*")
            .eq("case_id", case_id)
            .order("page_number")
            .execute()
        )
        return {"deadlines": result.data or []}
    except Exception as e:
        print(f"[deadlines] get_deadlines error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch deadlines")
