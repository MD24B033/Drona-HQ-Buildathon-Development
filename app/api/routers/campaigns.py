"""Campaign, ICP, target-company and agent-configuration endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from agents.registry import ensure_campaign_agents
from core.auth import get_current_profile, require_campaign, require_icp
from core.config import AGENT_TYPES
from db.supabase_client import supabase
from schemas import (
    CampaignAgentUpdate,
    CampaignCompaniesUpdate,
    CampaignUpdate,
    CampaignWithICPCreate,
    ICPCreate,
    ICPUpdate,
)


router = APIRouter(prefix="/campaigns", tags=["campaigns"])


# ============================================================
# CAMPAIGNS
# ============================================================

@router.get("")
async def list_campaigns(
    profile: dict[str, Any] = Depends(get_current_profile),
):
    """Every campaign owned by the caller, newest first."""

    response = (
        supabase
        .table("campaigns")
        .select("*")
        .eq("profile_id", profile["id"])
        .order("created_at", desc=True)
        .execute()
    )

    campaigns = response.data or []

    # Attach the counts the campaign list cards show.
    for campaign in campaigns:
        campaign["icp_count"] = _count(
            "icps", "campaign_id", campaign["id"]
        )

        campaign["company_count"] = _count(
            "campaign_companies", "campaign_id", campaign["id"]
        )

    return {"campaigns": campaigns}


@router.post("", status_code=201)
async def create_campaign(
    body: CampaignWithICPCreate,
    profile: dict[str, Any] = Depends(get_current_profile),
):
    """Create a campaign together with its first ICP.

    A campaign without an ICP cannot run any agent, so the two are
    created as one unit and rolled back together.
    """

    payload = body.model_dump(exclude={"icp"})

    payload["profile_id"] = profile["id"]

    response = (
        supabase
        .table("campaigns")
        .insert(payload)
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=500,
            detail="Unable to create campaign.",
        )

    campaign = response.data[0]

    try:
        icp_response = (
            supabase
            .table("icps")
            .insert(
                {
                    "campaign_id": campaign["id"],
                    **body.icp.model_dump(),
                }
            )
            .execute()
        )

        if not icp_response.data:
            raise RuntimeError("Unable to create the first ICP.")

    except Exception as exc:
        # Do not leave a campaign behind that can never run.
        supabase.table("campaigns").delete().eq(
            "id", campaign["id"]
        ).execute()

        raise HTTPException(status_code=500, detail=str(exc))

    try:
        ensure_campaign_agents(campaign["id"])
    except Exception as exc:
        print("[CAMPAIGNS] Failed to seed campaign agents:", exc)

    return {
        "campaign": campaign,
        "icp": icp_response.data[0],
    }


@router.get("/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    profile: dict[str, Any] = Depends(get_current_profile),
):
    """A campaign plus everything the detail page renders."""

    campaign = require_campaign(campaign_id, profile["id"])

    icps = (
        supabase
        .table("icps")
        .select("*")
        .eq("campaign_id", campaign_id)
        .order("created_at", desc=False)
        .execute()
    )

    campaign_companies = (
        supabase
        .table("campaign_companies")
        .select("company_id, companies(*)")
        .eq("campaign_id", campaign_id)
        .execute()
    )

    rows = campaign_companies.data or []

    agents = (
        supabase
        .table("campaign_agents")
        .select("*")
        .eq("campaign_id", campaign_id)
        .execute()
        .data
        or []
    )

    # Campaigns created before the agent table was seeded still need
    # their default rows.
    if len(agents) < len(AGENT_TYPES):
        try:
            agents = ensure_campaign_agents(campaign_id)
        except Exception as exc:
            print("[CAMPAIGNS] Failed to seed campaign agents:", exc)

    return {
        "campaign": campaign,
        "icps": icps.data or [],
        "companies": [
            row["companies"]
            for row in rows
            if row.get("companies")
        ],
        "company_ids": [
            row["company_id"]
            for row in rows
            if row.get("company_id")
        ],
        "agents": agents,
        "stats": _campaign_stats(campaign_id),
    }


@router.patch("/{campaign_id}")
async def update_campaign(
    campaign_id: str,
    body: CampaignUpdate,
    profile: dict[str, Any] = Depends(get_current_profile),
):
    require_campaign(campaign_id, profile["id"])

    payload = body.model_dump(exclude_none=True)

    if not payload:
        raise HTTPException(
            status_code=400,
            detail="No fields to update.",
        )

    response = (
        supabase
        .table("campaigns")
        .update(payload)
        .eq("id", campaign_id)
        .execute()
    )

    return {"campaign": response.data[0] if response.data else None}


@router.delete("/{campaign_id}", status_code=204)
async def delete_campaign(
    campaign_id: str,
    profile: dict[str, Any] = Depends(get_current_profile),
):
    require_campaign(campaign_id, profile["id"])

    supabase.table("campaigns").delete().eq("id", campaign_id).execute()


# ============================================================
# ICPS
# ============================================================

@router.get("/{campaign_id}/icps")
async def list_icps(
    campaign_id: str,
    profile: dict[str, Any] = Depends(get_current_profile),
):
    require_campaign(campaign_id, profile["id"])

    response = (
        supabase
        .table("icps")
        .select("*")
        .eq("campaign_id", campaign_id)
        .order("created_at", desc=False)
        .execute()
    )

    return {"icps": response.data or []}


@router.post("/{campaign_id}/icps", status_code=201)
async def create_icp(
    campaign_id: str,
    body: ICPCreate,
    profile: dict[str, Any] = Depends(get_current_profile),
):
    require_campaign(campaign_id, profile["id"])

    response = (
        supabase
        .table("icps")
        .insert({"campaign_id": campaign_id, **body.model_dump()})
        .execute()
    )

    if not response.data:
        raise HTTPException(status_code=500, detail="Unable to create ICP.")

    return {"icp": response.data[0]}


@router.get("/{campaign_id}/icps/{icp_id}")
async def get_icp(
    campaign_id: str,
    icp_id: str,
    profile: dict[str, Any] = Depends(get_current_profile),
):
    require_campaign(campaign_id, profile["id"])

    icp = require_icp(icp_id, profile["id"])

    return {"icp": icp}


@router.patch("/{campaign_id}/icps/{icp_id}")
async def update_icp(
    campaign_id: str,
    icp_id: str,
    body: ICPUpdate,
    profile: dict[str, Any] = Depends(get_current_profile),
):
    require_campaign(campaign_id, profile["id"])

    require_icp(icp_id, profile["id"])

    payload = body.model_dump(exclude_none=True)

    if not payload:
        raise HTTPException(
            status_code=400,
            detail="No fields to update.",
        )

    response = (
        supabase
        .table("icps")
        .update(payload)
        .eq("id", icp_id)
        .execute()
    )

    return {"icp": response.data[0] if response.data else None}


@router.delete("/{campaign_id}/icps/{icp_id}", status_code=204)
async def delete_icp(
    campaign_id: str,
    icp_id: str,
    profile: dict[str, Any] = Depends(get_current_profile),
):
    require_campaign(campaign_id, profile["id"])

    require_icp(icp_id, profile["id"])

    remaining = (
        supabase
        .table("icps")
        .select("id")
        .eq("campaign_id", campaign_id)
        .execute()
    )

    if len(remaining.data or []) <= 1:
        raise HTTPException(
            status_code=400,
            detail="A campaign must keep at least one ICP.",
        )

    supabase.table("icps").delete().eq("id", icp_id).execute()


# ============================================================
# TARGET COMPANIES
# ============================================================

@router.get("/{campaign_id}/companies")
async def list_campaign_companies(
    campaign_id: str,
    profile: dict[str, Any] = Depends(get_current_profile),
):
    require_campaign(campaign_id, profile["id"])

    response = (
        supabase
        .table("campaign_companies")
        .select("company_id, companies(*)")
        .eq("campaign_id", campaign_id)
        .execute()
    )

    rows = response.data or []

    return {
        "companies": [
            row["companies"]
            for row in rows
            if row.get("companies")
        ],
        "company_ids": [
            row["company_id"]
            for row in rows
            if row.get("company_id")
        ],
    }


@router.put("/{campaign_id}/companies")
async def set_campaign_companies(
    campaign_id: str,
    body: CampaignCompaniesUpdate,
    profile: dict[str, Any] = Depends(get_current_profile),
):
    """Replace this campaign's target company selection."""

    require_campaign(campaign_id, profile["id"])

    company_ids = list(dict.fromkeys(body.company_ids))

    if company_ids:
        # Reject ids that do not exist rather than failing on the FK.
        existing = (
            supabase
            .table("companies")
            .select("id")
            .in_("id", company_ids)
            .execute()
        )

        known = {row["id"] for row in (existing.data or [])}

        unknown = [
            company_id
            for company_id in company_ids
            if company_id not in known
        ]

        if unknown:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown company ids: {unknown}",
            )

    (
        supabase
        .table("campaign_companies")
        .delete()
        .eq("campaign_id", campaign_id)
        .execute()
    )

    if company_ids:
        (
            supabase
            .table("campaign_companies")
            .insert(
                [
                    {
                        "campaign_id": campaign_id,
                        "company_id": company_id,
                    }
                    for company_id in company_ids
                ]
            )
            .execute()
        )

    return {"company_ids": company_ids}


# ============================================================
# AGENT CONFIGURATION
# ============================================================

@router.get("/{campaign_id}/agents")
async def list_campaign_agents(
    campaign_id: str,
    profile: dict[str, Any] = Depends(get_current_profile),
):
    require_campaign(campaign_id, profile["id"])

    response = (
        supabase
        .table("campaign_agents")
        .select("*")
        .eq("campaign_id", campaign_id)
        .execute()
    )

    agents = response.data or []

    # Seed the defaults the first time this campaign is opened.
    if len(agents) < len(AGENT_TYPES):
        agents = ensure_campaign_agents(campaign_id)

    return {"agents": agents}


@router.patch("/{campaign_id}/agents/{agent_type}")
async def update_campaign_agent(
    campaign_id: str,
    agent_type: str,
    body: CampaignAgentUpdate,
    profile: dict[str, Any] = Depends(get_current_profile),
):
    require_campaign(campaign_id, profile["id"])

    if agent_type not in AGENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown agent type: {agent_type}",
        )

    payload = body.model_dump(exclude_none=True)

    if not payload:
        raise HTTPException(
            status_code=400,
            detail="No fields to update.",
        )

    response = (
        supabase
        .table("campaign_agents")
        .upsert(
            {
                "campaign_id": campaign_id,
                "agent_type": agent_type,
                **payload,
            },
            on_conflict="campaign_id,agent_type",
        )
        .execute()
    )

    return {"agent": response.data[0] if response.data else None}


# ============================================================
# HELPERS
# ============================================================

def _count(table: str, column: str, value: str) -> int:

    try:
        response = (
            supabase
            .table(table)
            .select(column, count="exact")
            .eq(column, value)
            .limit(0)
            .execute()
        )

        return response.count or 0

    except Exception:
        return 0


def _campaign_stats(campaign_id: str) -> dict[str, int]:
    """Headline counters for the campaign dashboard."""

    icps = (
        supabase
        .table("icps")
        .select("id")
        .eq("campaign_id", campaign_id)
        .execute()
    )

    icp_ids = [row["id"] for row in (icps.data or [])]

    matches: list[dict[str, Any]] = []

    if icp_ids:
        matches_response = (
            supabase
            .table("prospect_icp_matches")
            .select("prospect_id, decision, status")
            .in_("icp_id", icp_ids)
            .execute()
        )

        matches = matches_response.data or []

    qualified_ids = {
        match["prospect_id"]
        for match in matches
        if match.get("decision") == "qualified"
        and match.get("status") == "completed"
    }

    return {
        "icps": len(icp_ids),
        "companies": _count(
            "campaign_companies", "campaign_id", campaign_id
        ),
        "evaluated_prospects": len(
            {match["prospect_id"] for match in matches}
        ),
        "qualified_prospects": len(qualified_ids),
        "researched_prospects": _count(
            "prospect_research", "campaign_id", campaign_id
        ),
        "planned_outreach": _count(
            "outreach_strategies", "campaign_id", campaign_id
        ),
        "conversations": _count(
            "conversations", "campaign_id", campaign_id
        ),
        "knowledge_documents": _count(
            "knowledge_documents", "campaign_id", campaign_id
        ),
    }
