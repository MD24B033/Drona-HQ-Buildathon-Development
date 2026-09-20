"""Company and prospect endpoints.

Companies and prospects are a shared pool rather than per-profile data,
so these routes only require a signed-in caller.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from core.auth import get_current_profile, require_campaign
from db.supabase_client import supabase
from schemas import CompanyCreate


router = APIRouter(tags=["companies"])


# ============================================================
# COMPANIES
# ============================================================

@router.get("/companies")
async def list_companies(
    search: str | None = Query(default=None),
    limit: int = Query(default=200, le=1000),
    profile: dict[str, Any] = Depends(get_current_profile),
):
    query = (
        supabase
        .table("companies")
        .select("*")
        .order("name", desc=False)
        .limit(limit)
    )

    if search:
        query = query.ilike("name", f"%{search}%")

    response = query.execute()

    return {"companies": response.data or []}


@router.post("/companies", status_code=201)
async def create_company(
    body: CompanyCreate,
    profile: dict[str, Any] = Depends(get_current_profile),
):
    response = (
        supabase
        .table("companies")
        .insert(body.model_dump())
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=500,
            detail="Unable to create company.",
        )

    return {"company": response.data[0]}


@router.get("/companies/{company_id}")
async def get_company(
    company_id: str,
    profile: dict[str, Any] = Depends(get_current_profile),
):
    response = (
        supabase
        .table("companies")
        .select("*, prospects(*)")
        .eq("id", company_id)
        .maybe_single()
        .execute()
    )

    company = response.data if response else None

    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")

    return {"company": company}


# ============================================================
# PROSPECTS
# ============================================================

@router.get("/prospects")
async def list_prospects(
    campaign_id: str = Query(...),
    decision: str | None = Query(default=None),
    limit: int = Query(default=200, le=1000),
    profile: dict[str, Any] = Depends(get_current_profile),
):
    """Prospects at a campaign's target companies, with their pipeline state.

    Each row carries the best ICP match, the research summary, the
    outreach strategy and the follow-up plan, so the prospects table can
    render without further round trips.
    """

    require_campaign(campaign_id, profile["id"])

    company_ids = [
        row["company_id"]
        for row in (
            supabase
            .table("campaign_companies")
            .select("company_id")
            .eq("campaign_id", campaign_id)
            .execute()
            .data
            or []
        )
        if row.get("company_id")
    ]

    if not company_ids:
        return {"prospects": [], "total": 0}

    prospects = (
        supabase
        .table("prospects")
        .select("*, companies(id, name, website, industry)")
        .in_("company_id", company_ids)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
        .data
        or []
    )

    prospect_ids = [prospect["id"] for prospect in prospects]

    if not prospect_ids:
        return {"prospects": [], "total": 0}

    icp_ids = [
        row["id"]
        for row in (
            supabase
            .table("icps")
            .select("id")
            .eq("campaign_id", campaign_id)
            .execute()
            .data
            or []
        )
    ]

    matches: list[dict[str, Any]] = []

    if icp_ids:
        matches = (
            supabase
            .table("prospect_icp_matches")
            .select("*, icps(id, name)")
            .in_("prospect_id", prospect_ids)
            .in_("icp_id", icp_ids)
            .order("match_score", desc=True)
            .execute()
            .data
            or []
        )

    best_match: dict[str, Any] = {}

    for match in matches:
        # Ordered by score, so the first one seen is the best one.
        best_match.setdefault(match["prospect_id"], match)

    research = _index("prospect_research", campaign_id, prospect_ids)
    strategies = _index("outreach_strategies", campaign_id, prospect_ids)
    followups = _index("followup_plans", campaign_id, prospect_ids)
    conversations = _index("conversations", campaign_id, prospect_ids)

    enriched = []

    for prospect in prospects:
        prospect_id = prospect["id"]

        match = best_match.get(prospect_id)

        if decision and (not match or match.get("decision") != decision):
            continue

        enriched.append(
            {
                **prospect,
                "icp_match": match,
                "research": research.get(prospect_id),
                "strategy": strategies.get(prospect_id),
                "followup": followups.get(prospect_id),
                "conversation": conversations.get(prospect_id),
            }
        )

    return {"prospects": enriched, "total": len(enriched)}


@router.get("/prospects/{prospect_id}")
async def get_prospect(
    prospect_id: str,
    campaign_id: str = Query(...),
    profile: dict[str, Any] = Depends(get_current_profile),
):
    """Everything known about one prospect inside one campaign."""

    require_campaign(campaign_id, profile["id"])

    response = (
        supabase
        .table("prospects")
        .select("*, companies(*)")
        .eq("id", prospect_id)
        .maybe_single()
        .execute()
    )

    prospect = response.data if response else None

    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found.")

    matches = (
        supabase
        .table("prospect_icp_matches")
        .select("*, icps!inner(id, name, campaign_id)")
        .eq("prospect_id", prospect_id)
        .eq("icps.campaign_id", campaign_id)
        .order("match_score", desc=True)
        .execute()
        .data
        or []
    )

    conversations = (
        supabase
        .table("conversations")
        .select("*, conversation_messages(*)")
        .eq("prospect_id", prospect_id)
        .eq("campaign_id", campaign_id)
        .order("created_at", desc=True)
        .execute()
        .data
        or []
    )

    return {
        "prospect": prospect,
        "icp_matches": matches,
        "research": _single(
            "prospect_research", campaign_id, prospect_id
        ),
        "strategy": _single(
            "outreach_strategies", campaign_id, prospect_id
        ),
        "followup": _single("followup_plans", campaign_id, prospect_id),
        "conversations": conversations,
    }


# ============================================================
# HELPERS
# ============================================================

def _index(
    table: str,
    campaign_id: str,
    prospect_ids: list[str],
) -> dict[str, dict[str, Any]]:
    """One query per table instead of one per prospect."""

    if not prospect_ids:
        return {}

    try:
        response = (
            supabase
            .table(table)
            .select("*")
            .eq("campaign_id", campaign_id)
            .in_("prospect_id", prospect_ids)
            .execute()
        )

        return {
            row["prospect_id"]: row
            for row in (response.data or [])
        }

    except Exception as exc:
        print(f"[COMPANIES] Failed to index {table}:", exc)

        return {}


def _single(
    table: str,
    campaign_id: str,
    prospect_id: str,
) -> dict[str, Any] | None:

    try:
        response = (
            supabase
            .table(table)
            .select("*")
            .eq("campaign_id", campaign_id)
            .eq("prospect_id", prospect_id)
            .maybe_single()
            .execute()
        )

        return response.data if response else None

    except Exception:
        return None
