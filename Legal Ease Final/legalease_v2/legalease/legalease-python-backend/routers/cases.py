"""
Cases router

GET    /api/cases              — list all cases with their documents
DELETE /api/cases/{case_id}    — permanently delete a case (cascades via FK)
"""
from fastapi import APIRouter, HTTPException
from lib.supabase_client import get_supabase

router = APIRouter()


@router.get("/cases")
async def get_cases():
    """
    Return all cases ordered newest-first, each with their documents list.
    Safer version: fetch cases first, then documents separately, so we don't
    depend on Supabase nested relationship resolution.
    """
    try:
        supabase = get_supabase()

        # Step 1: fetch cases only
        cases_result = (
            supabase.from_("cases")
            .select("id, title, status, summary, risk_score, risk_explanation, created_at")
            .order("created_at", desc=True)
            .execute()
        )

        cases = cases_result.data or []

        if not cases:
            return {"cases": []}

        # Step 2: fetch all documents separately
        docs_result = (
            supabase.from_("documents")
            .select("id, case_id, name, page_count, storage_path")
            .execute()
        )

        documents = docs_result.data or []

        # Step 3: attach documents to matching cases
        docs_by_case = {}
        for doc in documents:
            case_id = doc.get("case_id")
            if case_id not in docs_by_case:
                docs_by_case[case_id] = []
            docs_by_case[case_id].append({
                "id": doc.get("id"),
                "name": doc.get("name"),
                "page_count": doc.get("page_count"),
                "storage_path": doc.get("storage_path"),
            })

        for case in cases:
            case["documents"] = docs_by_case.get(case["id"], [])

        return {"cases": cases}

    except Exception as e:
        print(f"[cases] get_cases error: {repr(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch cases: {str(e)}")


@router.delete("/cases/{case_id}")
async def delete_case(case_id: str):
    """
    Delete a case and all related data (documents, chunks, messages).
    The schema uses ON DELETE CASCADE, so one delete is enough.
    """
    try:
        supabase = get_supabase()
        supabase.from_("cases").delete().eq("id", case_id).execute()
        return {"success": True}
    except Exception as e:
        print(f"[cases] delete_case error: {repr(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete case: {str(e)}")