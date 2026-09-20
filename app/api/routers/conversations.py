"""Conversation, message and activity-feed endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from core.auth import get_current_profile, require_campaign
from db.supabase_client import supabase


router = APIRouter(tags=["conversations"])


@router.get("/conversations")
async def list_conversations(
    campaign_id: str = Query(...),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    profile: dict[str, Any] = Depends(get_current_profile),
):
    require_campaign(campaign_id, profile["id"])

    query = (
        supabase
        .table("conversations")
        .select(
            "*, prospects(id, full_name, current_title, "
            "companies(id, name))"
        )
        .eq("campaign_id", campaign_id)
        .order("updated_at", desc=True)
        .limit(limit)
    )

    if status:
        query = query.eq("status", status)

    conversations = query.execute().data or []

    for conversation in conversations:
        conversation["message_count"] = _message_count(conversation["id"])

    return {"conversations": conversations}


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    profile: dict[str, Any] = Depends(get_current_profile),
):
    conversation = _require_conversation(conversation_id, profile["id"])

    messages = (
        supabase
        .table("conversation_messages")
        .select("*")
        .eq("conversation_id", conversation_id)
        .order("created_at", desc=False)
        .execute()
        .data
        or []
    )

    return {"conversation": conversation, "messages": messages}


@router.get("/events")
async def list_events(
    campaign_id: str = Query(...),
    limit: int = Query(default=100, le=500),
    profile: dict[str, Any] = Depends(get_current_profile),
):
    """The campaign activity feed."""

    require_campaign(campaign_id, profile["id"])

    events = (
        supabase
        .table("outreach_events")
        .select("*")
        .eq("campaign_id", campaign_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
        .data
        or []
    )

    return {"events": events}


@router.get("/followups")
async def list_followups(
    campaign_id: str = Query(...),
    profile: dict[str, Any] = Depends(get_current_profile),
):
    require_campaign(campaign_id, profile["id"])

    plans = (
        supabase
        .table("followup_plans")
        .select("*, prospects(id, full_name, current_title)")
        .eq("campaign_id", campaign_id)
        .order("next_action_at", desc=False)
        .execute()
        .data
        or []
    )

    return {"followups": plans}


@router.get("/strategies")
async def list_strategies(
    campaign_id: str = Query(...),
    profile: dict[str, Any] = Depends(get_current_profile),
):
    require_campaign(campaign_id, profile["id"])

    strategies = (
        supabase
        .table("outreach_strategies")
        .select("*, prospects(id, full_name, current_title)")
        .eq("campaign_id", campaign_id)
        .order("sequence_step", desc=False)
        .execute()
        .data
        or []
    )

    return {"strategies": strategies}


# ============================================================
# HELPERS
# ============================================================

def _require_conversation(
    conversation_id: str,
    profile_id: str,
) -> dict[str, Any]:

    response = (
        supabase
        .table("conversations")
        .select(
            "*, prospects(id, full_name, current_title, linkedin_url, "
            "companies(id, name)), campaigns!inner(id, profile_id)"
        )
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


def _message_count(conversation_id: str) -> int:

    try:
        response = (
            supabase
            .table("conversation_messages")
            .select("id", count="exact")
            .eq("conversation_id", conversation_id)
            .limit(0)
            .execute()
        )

        return response.count or 0

    except Exception:
        return 0
