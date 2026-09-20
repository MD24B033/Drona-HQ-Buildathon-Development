"""Agent execution endpoints.

Every route resolves the caller's campaign first, builds the agent from
its `campaign_agents` configuration, and records the execution in
`agent_runs`.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from agents.orchestrator import STAGES, run_pipeline
from agents.prospect_discovery.agent import run_prospect_discovery_batch
from agents.registry import build_agent
from core.auth import get_current_profile, require_campaign, require_icp
from core.gemini import QuotaExhaustedError, is_overloaded
from core.runs import track_run
from db.supabase_client import supabase
from schemas import (
    DiscoveryRequest,
    FollowupRequest,
    ICPFitmentRequest,
    OutreachRequest,
    PersonalizationRequest,
    PipelineRequest,
    ReplyRequest,
    ResearchRequest,
    StrategyRequest,
)


router = APIRouter(prefix="/agents", tags=["agents"])


def _agent_error(exc: Exception) -> HTTPException:
    """Map agent failures onto sensible HTTP statuses."""

    if isinstance(exc, PermissionError):
        return HTTPException(status_code=409, detail=str(exc))

    if isinstance(exc, ValueError):
        return HTTPException(status_code=404, detail=str(exc))

    if isinstance(exc, QuotaExhaustedError):
        return HTTPException(status_code=429, detail=str(exc))

    if is_overloaded(exc):
        return HTTPException(
            status_code=503,
            detail=(
                "The model is temporarily unavailable or rate limited. "
                "Please try again in a minute."
            ),
        )

    print("[AGENTS] Agent failed:", exc)

    return HTTPException(status_code=500, detail=str(exc))


# ============================================================
# PROSPECT DISCOVERY
# ============================================================

@router.post("/discovery/run")
async def run_discovery(
    body: DiscoveryRequest,
    profile: dict[str, Any] = Depends(get_current_profile),
):
    """Find new people at the campaign's target companies."""

    icp = require_icp(body.icp_id, profile["id"])

    campaign_id = icp["campaign_id"]

    company_ids = body.company_ids or _campaign_company_ids(campaign_id)

    if not company_ids:
        raise HTTPException(
            status_code=400,
            detail=(
                "Select at least one target company before running "
                "discovery."
            ),
        )

    try:
        async with track_run(
            agent_type="prospect_discovery",
            campaign_id=campaign_id,
            payload={
                "icp_id": body.icp_id,
                "company_ids": company_ids,
            },
        ) as run:
            results = await run_prospect_discovery_batch(
                company_ids=company_ids,
                icp_id=body.icp_id,
                run_fitment=body.run_fitment,
            )

            summary = {
                "companies": len(results),
                "discovered": sum(
                    result.get("discovered_count", 0)
                    for result in results
                ),
                "saved": sum(
                    result.get("saved_count", 0)
                    for result in results
                ),
            }

            run["output"] = summary

        return {
            "success": True,
            "agent": "prospect_discovery",
            "summary": summary,
            "results": results,
        }

    except Exception as exc:
        raise _agent_error(exc)


# ============================================================
# ICP FITMENT
# ============================================================

@router.post("/icp-fitment/run")
async def run_icp_fitment(
    body: ICPFitmentRequest,
    profile: dict[str, Any] = Depends(get_current_profile),
):
    icp = require_icp(body.icp_id, profile["id"])

    campaign_id = icp["campaign_id"]

    try:
        agent = build_agent(campaign_id, "icp_fitment")

        async with track_run(
            agent_type="icp_fitment",
            campaign_id=campaign_id,
            payload=body.model_dump(),
            model=agent.model,
        ) as run:
            result = await agent.run(
                icp_id=body.icp_id,
                company_ids=body.company_ids,
                prospect_ids=body.prospect_ids,
            )

            run["output"] = result

        return {
            "success": True,
            "agent": "icp_fitment",
            "result": result,
        }

    except Exception as exc:
        raise _agent_error(exc)


@router.get("/icp-fitment/{icp_id}/results")
async def get_icp_fitment_results(
    icp_id: str,
    profile: dict[str, Any] = Depends(get_current_profile),
):
    """Scores for one ICP, with the counters the agent card shows."""

    require_icp(icp_id, profile["id"])

    try:
        response = (
            supabase
            .table("prospect_icp_matches")
            .select(
                """
                id,
                prospect_id,
                icp_id,
                match_score,
                confidence,
                decision,
                reasoning,
                evidence,
                status,
                evaluated_at,
                prospects (
                    id,
                    full_name,
                    current_title,
                    linkedin_url,
                    companies (
                        id,
                        name
                    )
                )
                """
            )
            .eq("icp_id", icp_id)
            .order("match_score", desc=True)
            .execute()
        )

        results = response.data or []

        def count(field: str, value: str) -> int:
            return sum(
                1
                for result in results
                if result.get(field) == value
            )

        return {
            "success": True,
            "metrics": {
                "total": len(results),
                "completed": count("status", "completed"),
                "qualified": count("decision", "qualified"),
                "disqualified": count("decision", "disqualified"),
                "needs_review": count("decision", "needs_review"),
                "processing": count("status", "processing"),
                "failed": count("status", "failed"),
            },
            "results": results,
        }

    except Exception as exc:
        print("[AGENTS] Failed to load ICP results:", exc)

        raise HTTPException(
            status_code=500,
            detail="Failed to load ICP fitment results.",
        )


# ============================================================
# RESEARCH
# ============================================================

@router.post("/research/run")
async def run_research(
    body: ResearchRequest,
    profile: dict[str, Any] = Depends(get_current_profile),
):
    require_campaign(body.campaign_id, profile["id"])

    try:
        agent = build_agent(body.campaign_id, "research")

        async with track_run(
            agent_type="research",
            campaign_id=body.campaign_id,
            prospect_id=body.prospect_id,
            payload=body.model_dump(),
            model=agent.model,
        ) as run:
            result = await agent.run(
                prospect_id=body.prospect_id,
                campaign_id=body.campaign_id,
            )

            run["output"] = result

        return result

    except Exception as exc:
        raise _agent_error(exc)


# ============================================================
# STRATEGY
# ============================================================

@router.post("/strategy/run")
async def run_strategy(
    body: StrategyRequest,
    profile: dict[str, Any] = Depends(get_current_profile),
):
    require_campaign(body.campaign_id, profile["id"])

    try:
        agent = build_agent(body.campaign_id, "strategy")

        async with track_run(
            agent_type="strategy",
            campaign_id=body.campaign_id,
            payload=body.model_dump(),
            model=agent.model,
        ) as run:
            result = await agent.run(campaign_id=body.campaign_id)

            run["output"] = result.get("strategy")

        return result

    except Exception as exc:
        raise _agent_error(exc)


# ============================================================
# PERSONALIZATION
# ============================================================

@router.post("/personalization/run")
async def run_personalization(
    body: PersonalizationRequest,
    profile: dict[str, Any] = Depends(get_current_profile),
):
    """Draft a message without sending it."""

    campaign_id = body.campaign_id

    if body.icp_id:
        campaign_id = require_icp(body.icp_id, profile["id"])["campaign_id"]

    if not campaign_id:
        raise HTTPException(
            status_code=400,
            detail="Either campaign_id or icp_id is required.",
        )

    require_campaign(campaign_id, profile["id"])

    try:
        agent = build_agent(campaign_id, "personalization")

        async with track_run(
            agent_type="personalization",
            campaign_id=campaign_id,
            prospect_id=body.prospect_id,
            payload=body.model_dump(),
            model=agent.model,
        ) as run:
            result = await agent.run(
                prospect_id=body.prospect_id,
                icp_id=body.icp_id,
                campaign_id=campaign_id,
            )

            run["output"] = result

        return result

    except Exception as exc:
        raise _agent_error(exc)


# ============================================================
# CONVERSATION
# ============================================================

@router.post("/conversation/outreach")
async def send_outreach(
    body: OutreachRequest,
    profile: dict[str, Any] = Depends(get_current_profile),
):
    """Draft and send the first message, opening a conversation."""

    require_campaign(body.campaign_id, profile["id"])

    try:
        agent = build_agent(body.campaign_id, "conversation")

        async with track_run(
            agent_type="conversation",
            campaign_id=body.campaign_id,
            prospect_id=body.prospect_id,
            payload=body.model_dump(),
            model=agent.model,
        ) as run:
            result = await agent.start_outreach(
                prospect_id=body.prospect_id,
                campaign_id=body.campaign_id,
                icp_id=body.icp_id,
                channel=body.channel,
            )

            run["output"] = result

        return result

    except Exception as exc:
        raise _agent_error(exc)


@router.post("/conversation/reply")
async def handle_reply(
    body: ReplyRequest,
    profile: dict[str, Any] = Depends(get_current_profile),
):
    """Record a prospect reply and let the agent decide what happens next."""

    conversation = _require_conversation(
        body.conversation_id,
        profile["id"],
    )

    campaign_id = conversation["campaign_id"]

    try:
        agent = build_agent(campaign_id, "conversation")

        async with track_run(
            agent_type="conversation",
            campaign_id=campaign_id,
            prospect_id=conversation["prospect_id"],
            payload=body.model_dump(),
            model=agent.model,
        ) as run:
            result = await agent.handle_reply(
                conversation_id=body.conversation_id,
                content=body.content,
                channel_message_id=body.channel_message_id,
            )

            run["output"] = result

        return result

    except Exception as exc:
        raise _agent_error(exc)


# ============================================================
# FOLLOW-UP
# ============================================================

@router.post("/followup/run")
async def run_followup(
    body: FollowupRequest,
    profile: dict[str, Any] = Depends(get_current_profile),
):
    require_campaign(body.campaign_id, profile["id"])

    try:
        agent = build_agent(body.campaign_id, "followup")

        async with track_run(
            agent_type="followup",
            campaign_id=body.campaign_id,
            prospect_id=body.prospect_id,
            payload=body.model_dump(),
            model=agent.model,
        ) as run:
            result = await agent.run(
                prospect_id=body.prospect_id,
                campaign_id=body.campaign_id,
                conversation_id=body.conversation_id,
            )

            run["output"] = result

        return result

    except Exception as exc:
        raise _agent_error(exc)


# ============================================================
# FULL PIPELINE
# ============================================================

@router.post("/pipeline/run")
async def run_full_pipeline(
    body: PipelineRequest,
    profile: dict[str, Any] = Depends(get_current_profile),
):
    """Run several agents in dependency order for one campaign."""

    require_campaign(body.campaign_id, profile["id"])

    if body.stages:
        unknown = [
            stage
            for stage in body.stages
            if stage not in STAGES
        ]

        if unknown:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown pipeline stages: {unknown}",
            )

    if body.icp_id:
        require_icp(body.icp_id, profile["id"])

    try:
        return await run_pipeline(
            campaign_id=body.campaign_id,
            stages=body.stages,
            icp_id=body.icp_id,
            send_outreach=body.send_outreach,
        )

    except Exception as exc:
        raise _agent_error(exc)


@router.get("/pipeline/stages")
async def list_pipeline_stages():
    return {"stages": STAGES}


# ============================================================
# RUN HISTORY
# ============================================================

@router.get("/runs")
async def list_agent_runs(
    campaign_id: str = Query(...),
    agent_type: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    profile: dict[str, Any] = Depends(get_current_profile),
):
    require_campaign(campaign_id, profile["id"])

    query = (
        supabase
        .table("agent_runs")
        .select(
            "id, campaign_id, prospect_id, agent_type, status, error, "
            "started_at, completed_at, latency_ms, model"
        )
        .eq("campaign_id", campaign_id)
        .order("started_at", desc=True)
        .limit(limit)
    )

    if agent_type:
        query = query.eq("agent_type", agent_type)

    return {"runs": query.execute().data or []}


@router.get("/runs/{run_id}")
async def get_agent_run(
    run_id: str,
    profile: dict[str, Any] = Depends(get_current_profile),
):
    response = (
        supabase
        .table("agent_runs")
        .select("*, campaigns!inner(id, profile_id)")
        .eq("id", run_id)
        .eq("campaigns.profile_id", profile["id"])
        .maybe_single()
        .execute()
    )

    run = response.data if response else None

    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found.")

    return {"run": run}


# ============================================================
# HELPERS
# ============================================================

def _campaign_company_ids(campaign_id: str) -> list[str]:

    response = (
        supabase
        .table("campaign_companies")
        .select("company_id")
        .eq("campaign_id", campaign_id)
        .execute()
    )

    return [
        row["company_id"]
        for row in (response.data or [])
        if row.get("company_id")
    ]


def _require_conversation(
    conversation_id: str,
    profile_id: str,
) -> dict[str, Any]:

    response = (
        supabase
        .table("conversations")
        .select("*, campaigns!inner(id, profile_id)")
        .eq("id", conversation_id)
        .eq("campaigns.profile_id", profile_id)
        .maybe_single()
        .execute()
    )

    conversation = response.data if response else None

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    return conversation
