"""Outreach Strategy Agent.

Decides who to contact today, on which channel and in what order, then
writes the plan to `outreach_strategies`. The application - not the
model - owns the hard daily limits.
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from core.config import (
    DEFAULT_DAILY_TARGET,
    MAX_DAILY_TARGET,
    STRATEGY_MIN_CONFIDENCE,
    STRATEGY_MIN_MATCH_SCORE,
    model_for,
)
from core.gemini import generate_json
from db.supabase_client import supabase
from rag.retrieval import format_knowledge_context, retrieve_knowledge


CONTACT_EVENT_TYPES = {
    "message_sent",
    "outreach_sent",
    "email_sent",
    "linkedin_sent",
    "voice_call",
}

VALID_CHANNELS = {"email", "linkedin", "sms", "voice"}


class StrategyAgent:

    agent_type = "strategy"

    def __init__(self, system_prompt: str | None = None):
        self.model = model_for("strategy")
        self.system_prompt = system_prompt

    async def run(self, campaign_id: str) -> dict[str, Any]:

        context = await asyncio.to_thread(
            self._load_campaign_context,
            campaign_id,
        )

        eligible_prospects = self._get_eligible_prospects(context)

        usage = await asyncio.to_thread(self._calculate_usage, context)

        target_count = self._calculate_target_count(
            context,
            eligible_prospects,
            usage,
        )

        selected_prospects = eligible_prospects[:target_count]

        rag_chunks = await self._retrieve_rag(context, selected_prospects)

        if selected_prospects:
            gemini_strategy = await generate_json(
                model=self.model,
                prompt=self._build_prompt(
                    context=context,
                    prospects=selected_prospects,
                    usage=usage,
                    rag_context=format_knowledge_context(rag_chunks),
                ),
                system_instruction=self.system_prompt,
            )
        else:
            gemini_strategy = {
                "campaign_status": "stopped",
                "daily_target": 0,
                "reason": "No eligible prospects are available.",
                "prospects": [],
            }

        final_strategy = self._apply_hard_limits(
            prospects=selected_prospects,
            usage=usage,
            gemini_strategy=gemini_strategy,
        )

        stored = await asyncio.to_thread(
            self._store_strategies,
            campaign_id,
            final_strategy["prospects"],
        )

        return {
            "success": True,
            "agent": "strategy",
            "campaign_id": campaign_id,
            "strategy": {
                "campaign_status": final_strategy["campaign_status"],
                "reason": final_strategy["reason"],
                "daily_target": final_strategy["daily_target"],
                "remaining_capacity": final_strategy[
                    "remaining_capacity"
                ],
                "eligible_prospects": len(eligible_prospects),
                "selected_prospects": len(selected_prospects),
                "prospects": stored,
            },
            "usage": usage,
            "rag_chunks_used": len(rag_chunks),
        }

    # ========================================================
    # CONTEXT
    # ========================================================

    def _load_campaign_context(self, campaign_id: str) -> dict[str, Any]:

        campaign_response = (
            supabase
            .table("campaigns")
            .select("*")
            .eq("id", campaign_id)
            .maybe_single()
            .execute()
        )

        if not campaign_response or not campaign_response.data:
            raise ValueError("Campaign not found")

        campaign = campaign_response.data

        # `icps!inner` is required: without the inner join PostgREST
        # would return every match and merely null out the embedded ICP,
        # so prospects from other campaigns would leak in.
        matches_response = (
            supabase
            .table("prospect_icp_matches")
            .select(
                """
                *,
                prospects!inner (
                    id,
                    company_id,
                    full_name,
                    current_title,
                    linkedin_url,
                    country,
                    city,
                    functional_area,
                    areas_of_expertise,
                    context
                ),
                icps!inner (
                    id,
                    campaign_id,
                    name,
                    description,
                    criteria
                )
                """
            )
            .eq("icps.campaign_id", campaign_id)
            .eq("decision", "qualified")
            .eq("status", "completed")
            .order("match_score", desc=True)
            .execute()
        )

        matches = matches_response.data or []

        prospect_ids = [
            match["prospects"]["id"]
            for match in matches
            if match.get("prospects")
        ]

        research_by_prospect = self._index_by_prospect(
            "prospect_research",
            campaign_id,
            prospect_ids,
        )

        strategy_by_prospect = self._index_by_prospect(
            "outreach_strategies",
            campaign_id,
            prospect_ids,
        )

        prospects = []

        for match in matches:
            prospect = match.get("prospects")

            if not prospect:
                continue

            prospects.append(
                {
                    "prospect": prospect,
                    "icp_match": match,
                    "research": research_by_prospect.get(prospect["id"]),
                    "existing_strategy": strategy_by_prospect.get(
                        prospect["id"]
                    ),
                }
            )

        return {
            "campaign": campaign,
            "prospects": prospects,
        }

    def _index_by_prospect(
        self,
        table: str,
        campaign_id: str,
        prospect_ids: list[str],
    ) -> dict[str, dict[str, Any]]:
        """Fetch a per-prospect table in one query instead of N."""

        if not prospect_ids:
            return {}

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

    # ========================================================
    # ELIGIBILITY
    # ========================================================

    def _get_eligible_prospects(
        self,
        context: dict[str, Any],
    ) -> list[dict]:

        eligible = []

        for item in context["prospects"]:
            match = item["icp_match"]
            prospect = item["prospect"]

            if match.get("decision") != "qualified":
                continue

            if match.get("status") != "completed":
                continue

            score = float(match.get("match_score") or 0)
            confidence = float(match.get("confidence") or 0)

            if score < STRATEGY_MIN_MATCH_SCORE:
                continue

            if confidence < STRATEGY_MIN_CONFIDENCE:
                continue

            if not prospect.get("full_name"):
                continue

            existing = item.get("existing_strategy")

            if existing and existing.get("should_contact") is False:
                continue

            item["priority_score"] = score * 0.7 + confidence * 0.3

            if item.get("research"):
                item["priority_score"] += 5

            eligible.append(item)

        eligible.sort(
            key=lambda item: item["priority_score"],
            reverse=True,
        )

        return eligible

    # ========================================================
    # CAPACITY
    # ========================================================

    def _calculate_usage(self, context: dict[str, Any]) -> dict[str, Any]:

        campaign = context["campaign"]

        try:
            daily_limit = int(campaign.get("daily_limits") or 50)
        except (TypeError, ValueError):
            daily_limit = 50

        # Limits are *daily*, so only today's events count against them.
        since = (
            datetime.now(timezone.utc) - timedelta(days=1)
        ).isoformat()

        events_response = (
            supabase
            .table("outreach_events")
            .select(
                "id, prospect_id, channel, event_type, status, created_at"
            )
            .eq("campaign_id", campaign["id"])
            .gte("created_at", since)
            .execute()
        )

        events = events_response.data or []

        contact_events = [
            event
            for event in events
            if event.get("event_type") in CONTACT_EVENT_TYPES
        ]

        channel_usage: dict[str, int] = {}

        for event in contact_events:
            channel = event.get("channel") or "unknown"

            channel_usage[channel] = channel_usage.get(channel, 0) + 1

        return {
            "daily_limit": daily_limit,
            "contacts_used": len(contact_events),
            "remaining_capacity": max(
                daily_limit - len(contact_events),
                0,
            ),
            "channel_usage": channel_usage,
            "total_events": len(events),
        }

    def _calculate_target_count(
        self,
        context: dict[str, Any],
        prospects: list[dict],
        usage: dict[str, Any],
    ) -> int:

        remaining = usage["remaining_capacity"]

        if remaining <= 0:
            return 0

        channel_configuration = (
            context["campaign"].get("channel_configuration") or {}
        )

        configured_target = channel_configuration.get("daily_target")

        try:
            configured_target = int(
                configured_target
                if configured_target is not None
                else DEFAULT_DAILY_TARGET
            )
        except (TypeError, ValueError):
            configured_target = DEFAULT_DAILY_TARGET

        configured_target = min(configured_target, MAX_DAILY_TARGET)

        return max(
            0,
            min(configured_target, remaining, len(prospects)),
        )

    # ========================================================
    # RAG
    # ========================================================

    async def _retrieve_rag(
        self,
        context: dict[str, Any],
        prospects: list[dict],
    ) -> list[dict]:

        campaign = context["campaign"]

        query = {
            "objective": campaign.get("objective"),
            "target_personas": campaign.get("target_personas") or [],
            "geography": campaign.get("geography") or [],
            "qualification_criteria": campaign.get(
                "qualification_criteria"
            )
            or [],
            "outreach_strategy": campaign.get("outreach_strategy"),
            "prospects": [
                {
                    "name": item["prospect"].get("full_name"),
                    "title": item["prospect"].get("current_title"),
                    "score": item["icp_match"].get("match_score"),
                }
                for item in prospects
            ],
        }

        return await retrieve_knowledge(
            campaign_id=campaign["id"],
            query=json.dumps(query, default=str),
        )

    # ========================================================
    # PROMPT
    # ========================================================

    def _build_prompt(
        self,
        context: dict[str, Any],
        prospects: list[dict],
        usage: dict[str, Any],
        rag_context: str,
    ) -> str:

        campaign_json = json.dumps(
            context["campaign"], indent=2, default=str
        )
        usage_json = json.dumps(usage, indent=2, default=str)
        prospects_json = json.dumps(prospects, indent=2, default=str)

        return f"""
You are the Strategy Agent for a B2B autonomous SDR.

Determine the safest and most effective outreach strategy for the
supplied qualified prospects, using the campaign rules and evidence.

You must respect the hard limits provided by the application, which has
already calculated the maximum available daily capacity.

Decide: whether outreach should continue, how many prospects to target,
their priority, the primary and secondary channels, the objective, the
sequence step, the delay, the reason, and any constraints.

Do not invent prospect facts.
Do not exceed the supplied remaining capacity.
Do not target prospects that are not qualified.

Return JSON only:

{{
    "campaign_status": "active",
    "daily_target": 0,
    "reason": "",
    "prospects": [
        {{
            "prospect_id": "",
            "should_contact": true,
            "primary_channel": "email",
            "secondary_channel": null,
            "objective": "",
            "sequence_step": 1,
            "delay_hours": 0,
            "strategy_reason": "",
            "constraints": {{}}
        }}
    ]
}}

campaign_status must be either "active" or "stopped".
primary_channel and secondary_channel must be one of
email, linkedin, sms, voice (or null for secondary_channel).

campaign:

{campaign_json}

usage:

{usage_json}

eligible prospects:

{prospects_json}

retrieved campaign knowledge:

{rag_context}
"""

    # ========================================================
    # HARD LIMITS
    # ========================================================

    def _apply_hard_limits(
        self,
        prospects: list[dict],
        usage: dict[str, Any],
        gemini_strategy: dict,
    ) -> dict:

        remaining = usage["remaining_capacity"]

        if remaining <= 0:
            return {
                "campaign_status": "stopped",
                "reason": "Daily outreach capacity has been reached.",
                "daily_target": 0,
                "remaining_capacity": 0,
                "prospects": [],
            }

        allowed_ids = {item["prospect"]["id"] for item in prospects}

        final_prospects = []

        for strategy in gemini_strategy.get("prospects") or []:

            if not isinstance(strategy, dict):
                continue

            if strategy.get("prospect_id") not in allowed_ids:
                continue

            if not strategy.get("should_contact", False):
                continue

            if len(final_prospects) >= remaining:
                break

            final_prospects.append(self._sanitize(strategy))

        daily_target = min(len(final_prospects), remaining)

        reason = gemini_strategy.get("reason") or ""

        if not final_prospects:
            reason = (
                reason
                or "No eligible prospects remain for outreach."
            )

        return {
            "campaign_status": "active" if daily_target else "stopped",
            "reason": reason,
            "daily_target": daily_target,
            "remaining_capacity": remaining,
            "prospects": final_prospects,
        }

    def _sanitize(self, strategy: dict[str, Any]) -> dict[str, Any]:

        def channel(key: str) -> str | None:
            value = strategy.get(key)

            return value if value in VALID_CHANNELS else None

        try:
            sequence_step = max(1, int(strategy.get("sequence_step") or 1))
        except (TypeError, ValueError):
            sequence_step = 1

        try:
            delay_hours = max(0, int(strategy.get("delay_hours") or 0))
        except (TypeError, ValueError):
            delay_hours = 0

        constraints = strategy.get("constraints")

        return {
            "prospect_id": strategy["prospect_id"],
            "should_contact": True,
            "primary_channel": channel("primary_channel") or "email",
            "secondary_channel": channel("secondary_channel"),
            "objective": strategy.get("objective"),
            "sequence_step": sequence_step,
            "delay_hours": delay_hours,
            "strategy_reason": strategy.get("strategy_reason"),
            "constraints": (
                constraints if isinstance(constraints, dict) else {}
            ),
        }

    # ========================================================
    # PERSISTENCE
    # ========================================================

    def _store_strategies(
        self,
        campaign_id: str,
        strategies: list[dict],
    ) -> list[dict]:

        if not strategies:
            return []

        rows = [
            {**strategy, "campaign_id": campaign_id}
            for strategy in strategies
        ]

        response = (
            supabase
            .table("outreach_strategies")
            .upsert(rows, on_conflict="prospect_id,campaign_id")
            .execute()
        )

        return response.data or []


async def generate_strategy(campaign_id: str) -> dict[str, Any]:

    return await StrategyAgent().run(campaign_id=campaign_id)
