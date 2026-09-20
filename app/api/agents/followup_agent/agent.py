"""Follow-up Agent.

Decides whether a prospect should be contacted again, on which channel
and when, and writes the plan to `followup_plans`.
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from core.config import model_for
from core.gemini import generate_json
from db.supabase_client import supabase
from rag.retrieval import format_knowledge_context, retrieve_knowledge


REQUIRED_FIELDS = [
    "should_follow_up",
    "current_step",
    "max_steps",
    "next_channel",
    "status",
    "reasoning",
    "confidence",
]

VALID_STATUSES = {"active", "paused", "completed", "stopped"}

VALID_CHANNELS = {"email", "linkedin", "sms", "voice"}

DEFAULT_MAX_STEPS = 3

DEFAULT_DELAY_HOURS = 48


class FollowupAgent:

    agent_type = "followup"

    def __init__(self, system_prompt: str | None = None):
        self.model = model_for("followup")
        self.system_prompt = system_prompt

    async def run(
        self,
        prospect_id: str,
        campaign_id: str,
        conversation_id: str | None = None,
    ) -> dict[str, Any]:

        context = await asyncio.to_thread(
            self._load_context,
            prospect_id,
            campaign_id,
            conversation_id,
        )

        rag_chunks = await retrieve_knowledge(
            campaign_id=campaign_id,
            query=self._build_rag_query(context),
        )

        result = await generate_json(
            model=self.model,
            prompt=self._build_prompt(
                context,
                format_knowledge_context(rag_chunks),
            ),
            system_instruction=self.system_prompt,
        )

        plan = self._normalize(result, context)

        stored = await asyncio.to_thread(
            self._store_followup,
            prospect_id,
            campaign_id,
            conversation_id or context.get("conversation_id"),
            plan,
        )

        return {
            "success": True,
            "agent": self.agent_type,
            "prospect_id": prospect_id,
            "campaign_id": campaign_id,
            "followup": stored,
            "should_follow_up": plan["should_follow_up"],
            "rag_chunks_used": len(rag_chunks),
        }

    # ========================================================
    # CONTEXT
    # ========================================================

    def _load_context(
        self,
        prospect_id: str,
        campaign_id: str,
        conversation_id: str | None,
    ) -> dict[str, Any]:

        campaign = (
            supabase
            .table("campaigns")
            .select("*")
            .eq("id", campaign_id)
            .maybe_single()
            .execute()
        )

        if not campaign or not campaign.data:
            raise ValueError("Campaign not found")

        prospect = (
            supabase
            .table("prospects")
            .select("*")
            .eq("id", prospect_id)
            .maybe_single()
            .execute()
        )

        if not prospect or not prospect.data:
            raise ValueError("Prospect not found")

        company = None

        if prospect.data.get("company_id"):
            company_response = (
                supabase
                .table("companies")
                .select("*")
                .eq("id", prospect.data["company_id"])
                .maybe_single()
                .execute()
            )

            company = company_response.data if company_response else None

        research = (
            supabase
            .table("prospect_research")
            .select("*")
            .eq("prospect_id", prospect_id)
            .eq("campaign_id", campaign_id)
            .maybe_single()
            .execute()
        )

        strategy = (
            supabase
            .table("outreach_strategies")
            .select("*")
            .eq("prospect_id", prospect_id)
            .eq("campaign_id", campaign_id)
            .maybe_single()
            .execute()
        )

        icp_response = (
            supabase
            .table("prospect_icp_matches")
            .select(
                """
                *,
                icps!inner (
                    id,
                    campaign_id,
                    name,
                    description,
                    criteria
                )
                """
            )
            .eq("prospect_id", prospect_id)
            .eq("icps.campaign_id", campaign_id)
            .order("match_score", desc=True)
            .limit(1)
            .execute()
        )

        conversation = None
        messages: list[dict[str, Any]] = []

        # Fall back to the prospect's most recent conversation in this
        # campaign when the caller did not name one.
        if not conversation_id:
            latest = (
                supabase
                .table("conversations")
                .select("*")
                .eq("prospect_id", prospect_id)
                .eq("campaign_id", campaign_id)
                .order("updated_at", desc=True)
                .limit(1)
                .execute()
            )

            if latest.data:
                conversation = latest.data[0]
                conversation_id = conversation["id"]

        elif conversation_id:
            conversation_response = (
                supabase
                .table("conversations")
                .select("*")
                .eq("id", conversation_id)
                .maybe_single()
                .execute()
            )

            conversation = (
                conversation_response.data
                if conversation_response
                else None
            )

        if conversation_id:
            messages_response = (
                supabase
                .table("conversation_messages")
                .select("*")
                .eq("conversation_id", conversation_id)
                .order("created_at", desc=False)
                .execute()
            )

            messages = messages_response.data or []

        existing_followup = (
            supabase
            .table("followup_plans")
            .select("*")
            .eq("prospect_id", prospect_id)
            .eq("campaign_id", campaign_id)
            .maybe_single()
            .execute()
        )

        return {
            "campaign": campaign.data,
            "prospect": prospect.data,
            "company": company,
            "research": research.data if research else None,
            "strategy": strategy.data if strategy else None,
            "icp_match": (
                icp_response.data[0] if icp_response.data else None
            ),
            "conversation": conversation,
            "conversation_id": conversation_id,
            "messages": messages,
            "existing_followup": (
                existing_followup.data if existing_followup else None
            ),
        }

    def _build_rag_query(self, context: dict[str, Any]) -> str:

        campaign = context["campaign"]
        prospect = context["prospect"]
        messages = context["messages"]

        latest_message = messages[-1]["content"] if messages else ""

        return "\n".join(
            [
                f"Campaign objective: {campaign.get('objective', '')}",
                "Campaign outreach strategy: "
                f"{campaign.get('outreach_strategy', '')}",
                f"Prospect title: {prospect.get('current_title', '')}",
                "Prospect functional area: "
                f"{prospect.get('functional_area', '')}",
                "Research: "
                f"{json.dumps(context['research'] or {}, default=str)}",
                "Strategy: "
                f"{json.dumps(context['strategy'] or {}, default=str)}",
                f"Latest conversation message: {latest_message}",
            ]
        )

    # ========================================================
    # PROMPT
    # ========================================================

    def _build_prompt(
        self,
        context: dict[str, Any],
        rag_context: str,
    ) -> str:

        def dump(key: str) -> str:
            return json.dumps(context[key], indent=2, default=str)

        return f"""
You are the Follow-up Agent for a B2B autonomous SDR.

Your job is to determine what should happen next with a prospect, using
only the supplied information: the campaign objective and outreach
strategy, the prospect, the research, the ICP fit, the outreach
strategy, the conversation history, any existing follow-up plan, and the
retrieved campaign knowledge.

Do not invent facts.

Determine whether another follow-up should happen, the next channel, the
delay before it, the current sequence step, whether the sequence should
stop, and why.

Stop the follow-up when the supplied information indicates that the
prospect should not be contacted, the conversation is closed or
escalated, the prospect asked not to be contacted, the sequence reached
its maximum, or another clear stop condition exists.

Return JSON only:

{{
    "should_follow_up": true,
    "current_step": 1,
    "max_steps": 3,
    "delay_hours": 48,
    "next_channel": "email",
    "status": "active",
    "stop_reason": null,
    "reasoning": "",
    "confidence": 0
}}

status must be one of: active, paused, completed, stopped.
next_channel must be one of: email, linkedin, sms, voice.
delay_hours is the number of hours to wait before the next touch.
confidence must be between 0 and 100.

CAMPAIGN:
{dump("campaign")}

PROSPECT:
{dump("prospect")}

COMPANY:
{dump("company")}

ICP MATCH:
{dump("icp_match")}

RESEARCH:
{dump("research")}

OUTREACH STRATEGY:
{dump("strategy")}

CONVERSATION:
{dump("conversation")}

MESSAGES:
{dump("messages")}

EXISTING FOLLOW-UP:
{dump("existing_followup")}

RELEVANT RAG KNOWLEDGE:
{rag_context}
"""

    # ========================================================
    # RESULT
    # ========================================================

    def _normalize(
        self,
        result: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:

        missing = [
            field
            for field in REQUIRED_FIELDS
            if field not in result
        ]

        if missing:
            raise RuntimeError(f"Missing follow-up fields: {missing}")

        status = result.get("status")

        if status not in VALID_STATUSES:
            status = "active"

        should_follow_up = bool(result.get("should_follow_up"))

        def positive_int(key: str, fallback: int) -> int:
            try:
                return max(1, int(result.get(key) or fallback))
            except (TypeError, ValueError):
                return fallback

        current_step = positive_int("current_step", 1)
        max_steps = positive_int("max_steps", DEFAULT_MAX_STEPS)

        if current_step > max_steps:
            current_step = max_steps

        # A sequence that has run its course is complete, whatever the
        # model said.
        if current_step >= max_steps and should_follow_up:
            should_follow_up = False
            status = "completed"

        next_channel = result.get("next_channel")

        if next_channel not in VALID_CHANNELS:
            strategy = context.get("strategy") or {}

            next_channel = strategy.get("primary_channel") or "email"

        next_action_at = None

        if should_follow_up and status == "active":
            try:
                delay_hours = max(
                    0,
                    int(result.get("delay_hours") or DEFAULT_DELAY_HOURS),
                )
            except (TypeError, ValueError):
                delay_hours = DEFAULT_DELAY_HOURS

            next_action_at = (
                datetime.now(timezone.utc)
                + timedelta(hours=delay_hours)
            ).isoformat()

        else:
            next_channel = None

        stop_reason = result.get("stop_reason")

        return {
            "should_follow_up": should_follow_up,
            "current_step": current_step,
            "max_steps": max_steps,
            "next_action_at": next_action_at,
            "next_channel": next_channel,
            "status": status,
            "stop_reason": str(stop_reason) if stop_reason else None,
            "reasoning": str(result.get("reasoning") or ""),
        }

    def _store_followup(
        self,
        prospect_id: str,
        campaign_id: str,
        conversation_id: str | None,
        plan: dict[str, Any],
    ) -> dict[str, Any]:

        payload = {
            "prospect_id": prospect_id,
            "campaign_id": campaign_id,
            "conversation_id": conversation_id,
            "current_step": plan["current_step"],
            "max_steps": plan["max_steps"],
            "next_action_at": plan["next_action_at"],
            "next_channel": plan["next_channel"],
            "status": plan["status"],
            "stop_reason": plan["stop_reason"],
            "reasoning": plan["reasoning"],
        }

        response = (
            supabase
            .table("followup_plans")
            .upsert(payload, on_conflict="prospect_id,campaign_id")
            .execute()
        )

        if not response.data:
            raise RuntimeError("Failed to store follow-up plan")

        return response.data[0]


async def plan_followup(
    prospect_id: str,
    campaign_id: str,
    conversation_id: str | None = None,
) -> dict[str, Any]:

    return await FollowupAgent().run(
        prospect_id=prospect_id,
        campaign_id=campaign_id,
        conversation_id=conversation_id,
    )
