import json
import os
from typing import Any

from google import genai
from google.genai import types

from db.supabase_client import supabase
from rag.retrieval import retrieve_knowledge, format_knowledge_context


class StrategyAgent:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")

        self.client = genai.Client(api_key=api_key)

        self.model = os.getenv(
            "STRATEGY_MODEL",
            "gemini-3.6-flash",
        )

        self.default_daily_target = int(
            os.getenv("DEFAULT_DAILY_TARGET", "20")
        )

        self.max_daily_target = int(
            os.getenv("MAX_DAILY_TARGET", "50")
        )

        self.max_contacts_per_prospect = int(
            os.getenv("MAX_CONTACTS_PER_PROSPECT", "3")
        )

    async def run(
        self,
        campaign_id: str,
    ) -> dict[str, Any]:

        context = await self._load_campaign_context(
            campaign_id
        )

        eligible_prospects = self._get_eligible_prospects(
            context
        )

        usage = self._calculate_usage(
            context
        )

        target_count = self._calculate_target_count(
            context,
            eligible_prospects,
            usage,
        )

        selected_prospects = eligible_prospects[
            :target_count
        ]

        rag_chunks = await self._retrieve_rag(
            context,
            selected_prospects,
        )

        rag_context = format_knowledge_context(
            rag_chunks
        )

        gemini_strategy = await self._generate_strategy(
            context=context,
            prospects=selected_prospects,
            usage=usage,
            rag_context=rag_context,
        )

        final_strategy = self._apply_hard_limits(
            context=context,
            prospects=selected_prospects,
            usage=usage,
            gemini_strategy=gemini_strategy,
        )

        stored = await self._store_strategies(
            campaign_id=campaign_id,
            strategies=final_strategy["prospects"],
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
                "eligible_prospects": len(
                    eligible_prospects
                ),
                "selected_prospects": len(
                    selected_prospects
                ),
                "prospects": stored,
            },
            "usage": usage,
            "rag_chunks_used": len(rag_chunks),
        }

    async def _load_campaign_context(
        self,
        campaign_id: str,
    ) -> dict[str, Any]:

        campaign_response = (
            supabase
            .table("campaigns")
            .select("*")
            .eq("id", campaign_id)
            .single()
            .execute()
        )

        campaign = campaign_response.data

        if not campaign:
            raise ValueError("Campaign not found")

        matches_response = (
            supabase
            .table("prospect_icp_matches")
            .select(
                """
                *,
                prospects (
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
                icps (
                    id,
                    campaign_id,
                    name,
                    description,
                    criteria
                )
                """
            )
            .eq(
                "icps.campaign_id",
                campaign_id,
            )
            .eq(
                "decision",
                "qualified",
            )
            .eq(
                "status",
                "completed",
            )
            .order(
                "match_score",
                desc=True,
            )
            .execute()
        )

        matches = matches_response.data or []

        prospects = []

        for match in matches:
            prospect = match.get("prospects")

            if not prospect:
                continue

            research_response = (
                supabase
                .table("prospect_research")
                .select("*")
                .eq(
                    "prospect_id",
                    prospect["id"],
                )
                .eq(
                    "campaign_id",
                    campaign_id,
                )
                .maybe_single()
                .execute()
            )

            research = research_response.data

            strategy_response = (
                supabase
                .table("outreach_strategies")
                .select("*")
                .eq(
                    "prospect_id",
                    prospect["id"],
                )
                .eq(
                    "campaign_id",
                    campaign_id,
                )
                .maybe_single()
                .execute()
            )

            existing_strategy = strategy_response.data

            prospects.append({
                "prospect": prospect,
                "icp_match": match,
                "research": research,
                "existing_strategy": existing_strategy,
            })

        return {
            "campaign": campaign,
            "prospects": prospects,
        }

    def _get_eligible_prospects(
        self,
        context: dict[str, Any],
    ) -> list[dict]:

        eligible = []

        for item in context["prospects"]:
            match = item["icp_match"]
            prospect = item["prospect"]
            research = item["research"]

            if match.get("decision") != "qualified":
                continue

            if match.get("status") != "completed":
                continue

            confidence = float(
                match.get("confidence") or 0
            )

            score = float(
                match.get("match_score") or 0
            )

            if score < 70:
                continue

            if confidence < 50:
                continue

            if not prospect.get("full_name"):
                continue

            existing = item.get(
                "existing_strategy"
            )

            if existing and existing.get(
                "should_contact"
            ) is False:
                continue

            item["priority_score"] = (
                score * 0.7
                + confidence * 0.3
            )

            if research:
                item["priority_score"] += 5

            eligible.append(item)

        eligible.sort(
            key=lambda item: item["priority_score"],
            reverse=True,
        )

        return eligible

    def _calculate_usage(
        self,
        context: dict[str, Any],
    ) -> dict[str, Any]:

        campaign = context["campaign"]

        daily_limit = int(
            campaign.get("daily_limits") or 50
        )

        events_response = (
            supabase
            .table("outreach_events")
            .select(
                "id, prospect_id, channel, event_type, status, created_at, payload"
            )
            .eq(
                "campaign_id",
                campaign["id"],
            )
            .execute()
        )

        events = events_response.data or []

        contact_events = [
            event
            for event in events
            if event.get("event_type") in {
                "message_sent",
                "outreach_sent",
                "email_sent",
                "linkedin_sent",
                "voice_call",
            }
        ]

        channel_usage = {}

        for event in contact_events:
            channel = event.get("channel") or "unknown"

            channel_usage[channel] = (
                channel_usage.get(channel, 0) + 1
            )

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

        campaign = context["campaign"]

        configured_target = (
            campaign
            .get("channel_configuration", {})
            .get("daily_target")
        )

        if configured_target is None:
            configured_target = self.default_daily_target

        configured_target = int(
            configured_target
        )

        configured_target = min(
            configured_target,
            self.max_daily_target,
        )

        return min(
            configured_target,
            remaining,
            len(prospects),
        )

    async def _retrieve_rag(
        self,
        context: dict[str, Any],
        prospects: list[dict],
    ) -> list[dict]:

        campaign = context["campaign"]

        query = {
            "objective": campaign.get("objective"),
            "target_personas": campaign.get(
                "target_personas",
                [],
            ),
            "geography": campaign.get(
                "geography",
                [],
            ),
            "qualification_criteria": campaign.get(
                "qualification_criteria",
                [],
            ),
            "outreach_strategy": campaign.get(
                "outreach_strategy"
            ),
            "prospects": [
                {
                    "name": item["prospect"].get(
                        "full_name"
                    ),
                    "title": item["prospect"].get(
                        "current_title"
                    ),
                    "score": item["icp_match"].get(
                        "match_score"
                    ),
                    "research": item.get(
                        "research"
                    ),
                }
                for item in prospects
            ],
        }

        embedding_query = json.dumps(
            query,
            default=str,
        )

        return await retrieve_knowledge(
            campaign_id=campaign["id"],
            query=embedding_query,
            top_k=8,
            min_similarity=0.35,
        )

    async def _generate_strategy(
        self,
        context: dict[str, Any],
        prospects: list[dict],
        usage: dict[str, Any],
        rag_context: str,
    ) -> dict:

        campaign = context["campaign"]

        prompt = f"""
You are the Strategy Agent for a B2B autonomous SDR.

Determine the safest and most effective outreach strategy for the supplied qualified prospects.

Use the supplied campaign rules and evidence.

You must respect the hard limits provided by the application.

The application has already calculated the maximum available daily capacity.

Your job is to determine:

- whether outreach should continue
- how many prospects should be targeted
- priority of prospects
- primary channel
- secondary channel
- objective
- sequence step
- delay
- reason
- constraints

Do not invent prospect facts.

Do not exceed the supplied remaining capacity.

Do not target prospects that are not qualified.

Do not recommend contacting prospects when the campaign should stop.

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

campaign:

{json.dumps(campaign, indent=2, default=str)}

usage:

{json.dumps(usage, indent=2, default=str)}

eligible prospects:

{json.dumps(prospects, indent=2, default=str)}

retrieved campaign knowledge:

{rag_context}
"""

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )

        if not response.text:
            raise RuntimeError(
                "Gemini returned an empty strategy response"
            )

        result = json.loads(response.text)

        if not isinstance(result, dict):
            raise RuntimeError(
                "Invalid strategy response"
            )

        if result.get("campaign_status") not in {
            "active",
            "stopped",
        }:
            raise RuntimeError(
                "Invalid campaign status"
            )

        return result

    def _apply_hard_limits(
        self,
        context: dict[str, Any],
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

        allowed_ids = {
            item["prospect"]["id"]
            for item in prospects
        }

        raw_prospects = (
            gemini_strategy.get("prospects")
            or []
        )

        final_prospects = []

        for strategy in raw_prospects:

            prospect_id = strategy.get(
                "prospect_id"
            )

            if prospect_id not in allowed_ids:
                continue

            if not strategy.get(
                "should_contact",
                False,
            ):
                continue

            if len(final_prospects) >= remaining:
                break

            if strategy.get(
                "sequence_step",
                1,
            ) < 1:
                strategy["sequence_step"] = 1

            final_prospects.append(strategy)

        daily_target = min(
            len(final_prospects),
            remaining,
        )

        campaign_status = (
            "active"
            if daily_target > 0
            else "stopped"
        )

        reason = gemini_strategy.get(
            "reason",
            "",
        )

        if not final_prospects:
            reason = (
                reason
                or "No eligible prospects remain for outreach."
            )

        return {
            "campaign_status": campaign_status,
            "reason": reason,
            "daily_target": daily_target,
            "remaining_capacity": remaining,
            "prospects": final_prospects,
        }

    async def _store_strategies(
        self,
        campaign_id: str,
        strategies: list[dict],
    ) -> list[dict]:

        if not strategies:
            return []

        rows = []

        for strategy in strategies:

            rows.append({
                "prospect_id": strategy[
                    "prospect_id"
                ],
                "campaign_id": campaign_id,
                "should_contact": strategy.get(
                    "should_contact",
                    True,
                ),
                "primary_channel": strategy.get(
                    "primary_channel"
                ),
                "secondary_channel": strategy.get(
                    "secondary_channel"
                ),
                "objective": strategy.get(
                    "objective"
                ),
                "sequence_step": strategy.get(
                    "sequence_step",
                    1,
                ),
                "delay_hours": strategy.get(
                    "delay_hours",
                    0,
                ),
                "strategy_reason": strategy.get(
                    "strategy_reason"
                ),
                "constraints": strategy.get(
                    "constraints",
                    {},
                ),
            })

        response = (
            supabase
            .table("outreach_strategies")
            .upsert(
                rows,
                on_conflict="prospect_id,campaign_id",
            )
            .execute()
        )

        return response.data or []


async def generate_strategy(
    campaign_id: str,
) -> dict[str, Any]:

    agent = StrategyAgent()

    return await agent.run(
        campaign_id=campaign_id,
    )