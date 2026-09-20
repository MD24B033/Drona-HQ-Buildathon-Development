import json
import os
from typing import Any

from google import genai
from google.genai import types

from db.supabase_client import supabase
from rag.retrieval import retrieve_knowledge, format_knowledge_context


class FollowupAgent:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")

        self.client = genai.Client(api_key=api_key)

        self.model = os.getenv(
            "FOLLOWUP_MODEL",
            "gemini-3.6-flash",
        )

    async def run(
        self,
        prospect_id: str,
        campaign_id: str,
        conversation_id: str | None = None,
    ) -> dict[str, Any]:

        context = await self._load_context(
            prospect_id,
            campaign_id,
            conversation_id,
        )

        rag_query = self._build_rag_query(context)

        rag_chunks = await retrieve_knowledge(
            campaign_id=campaign_id,
            query=rag_query,
            top_k=8,
            min_similarity=0.35,
        )

        rag_context = format_knowledge_context(
            rag_chunks
        )

        prompt = self._build_prompt(
            context,
            rag_context,
        )

        result = await self._generate(prompt)

        stored = await self._store_followup(
            prospect_id=prospect_id,
            campaign_id=campaign_id,
            conversation_id=conversation_id,
            result=result,
        )

        return {
            "success": True,
            "agent": "followup",
            "prospect_id": prospect_id,
            "campaign_id": campaign_id,
            "followup": stored,
            "rag_chunks_used": len(rag_chunks),
        }

    async def _load_context(
        self,
        prospect_id: str,
        campaign_id: str,
        conversation_id: str | None,
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

        prospect_response = (
            supabase
            .table("prospects")
            .select("*")
            .eq("id", prospect_id)
            .single()
            .execute()
        )

        prospect = prospect_response.data

        if not prospect:
            raise ValueError("Prospect not found")

        company = None

        if prospect.get("company_id"):
            company_response = (
                supabase
                .table("companies")
                .select("*")
                .eq(
                    "id",
                    prospect["company_id"],
                )
                .single()
                .execute()
            )

            company = company_response.data

        research_response = (
            supabase
            .table("prospect_research")
            .select("*")
            .eq("prospect_id", prospect_id)
            .eq("campaign_id", campaign_id)
            .maybe_single()
            .execute()
        )

        research = research_response.data

        strategy_response = (
            supabase
            .table("outreach_strategies")
            .select("*")
            .eq("prospect_id", prospect_id)
            .eq("campaign_id", campaign_id)
            .maybe_single()
            .execute()
        )

        strategy = strategy_response.data

        icp_response = (
            supabase
            .table("prospect_icp_matches")
            .select(
                """
                *,
                icps (
                    id,
                    name,
                    description,
                    criteria
                )
                """
            )
            .eq(
                "prospect_id",
                prospect_id,
            )
            .order(
                "match_score",
                desc=True,
            )
            .limit(1)
            .execute()
        )

        icp_match = (
            icp_response.data[0]
            if icp_response.data
            else None
        )

        conversation = None
        messages = []

        if conversation_id:
            conversation_response = (
                supabase
                .table("conversations")
                .select("*")
                .eq(
                    "id",
                    conversation_id,
                )
                .single()
                .execute()
            )

            conversation = conversation_response.data

            messages_response = (
                supabase
                .table("conversation_messages")
                .select("*")
                .eq(
                    "conversation_id",
                    conversation_id,
                )
                .order(
                    "created_at",
                    desc=False,
                )
                .execute()
            )

            messages = messages_response.data or []

        existing_followup_response = (
            supabase
            .table("followup_plans")
            .select("*")
            .eq(
                "prospect_id",
                prospect_id,
            )
            .eq(
                "campaign_id",
                campaign_id,
            )
            .maybe_single()
            .execute()
        )

        existing_followup = (
            existing_followup_response.data
        )

        return {
            "campaign": campaign,
            "prospect": prospect,
            "company": company,
            "research": research,
            "strategy": strategy,
            "icp_match": icp_match,
            "conversation": conversation,
            "messages": messages,
            "existing_followup": existing_followup,
        }

    def _build_rag_query(
        self,
        context: dict[str, Any],
    ) -> str:

        campaign = context["campaign"]
        prospect = context["prospect"]
        research = context["research"]
        strategy = context["strategy"]
        messages = context["messages"]

        latest_message = (
            messages[-1]["content"]
            if messages
            else ""
        )

        return "\n".join([
            f"Campaign objective: {campaign.get('objective', '')}",
            f"Campaign outreach strategy: {campaign.get('outreach_strategy', '')}",
            f"Prospect title: {prospect.get('current_title', '')}",
            f"Prospect functional area: {prospect.get('functional_area', '')}",
            f"Research: {json.dumps(research or {}, default=str)}",
            f"Strategy: {json.dumps(strategy or {}, default=str)}",
            f"Latest conversation message: {latest_message}",
        ])

    def _build_prompt(
        self,
        context: dict[str, Any],
        rag_context: str,
    ) -> str:

        return f"""
You are the Follow-up Agent for a B2B autonomous SDR.

Your job is to determine what should happen next with a prospect.

Use only the supplied information.

Consider:
- campaign objective
- campaign outreach strategy
- prospect
- research
- ICP fit
- outreach strategy
- conversation history
- existing follow-up plan
- retrieved campaign knowledge

Do not invent facts.

Determine:
- whether another follow-up should happen
- the next action
- the next channel
- the delay
- the current sequence step
- whether the sequence should stop
- the reason

Stop follow-up when the supplied information indicates:
- the prospect should not be contacted
- the conversation is closed
- the conversation is escalated
- the prospect explicitly asks not to be contacted
- the sequence has reached its maximum
- another clear stop condition exists

Return JSON only:

{{
    "should_follow_up": true,
    "current_step": 1,
    "max_steps": 3,
    "next_action_at": null,
    "next_channel": "email",
    "status": "active",
    "stop_reason": null,
    "reasoning": "",
    "confidence": 0
}}

status must be one of:

active
paused
completed
stopped

confidence must be between 0 and 100.

CAMPAIGN:
{json.dumps(context["campaign"], indent=2, default=str)}

PROSPECT:
{json.dumps(context["prospect"], indent=2, default=str)}

COMPANY:
{json.dumps(context["company"], indent=2, default=str)}

ICP MATCH:
{json.dumps(context["icp_match"], indent=2, default=str)}

RESEARCH:
{json.dumps(context["research"], indent=2, default=str)}

OUTREACH STRATEGY:
{json.dumps(context["strategy"], indent=2, default=str)}

CONVERSATION:
{json.dumps(context["conversation"], indent=2, default=str)}

MESSAGES:
{json.dumps(context["messages"], indent=2, default=str)}

EXISTING FOLLOW-UP:
{json.dumps(context["existing_followup"], indent=2, default=str)}

RELEVANT RAG KNOWLEDGE:
{rag_context}
"""

    async def _generate(
        self,
        prompt: str,
    ) -> dict[str, Any]:

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )

        if not response.text:
            raise RuntimeError(
                "Gemini returned an empty follow-up response"
            )

        result = json.loads(response.text)

        if not isinstance(result, dict):
            raise RuntimeError(
                "Invalid follow-up response"
            )

        required = [
            "should_follow_up",
            "current_step",
            "max_steps",
            "next_action_at",
            "next_channel",
            "status",
            "stop_reason",
            "reasoning",
            "confidence",
        ]

        missing = [
            field
            for field in required
            if field not in result
        ]

        if missing:
            raise RuntimeError(
                f"Missing follow-up fields: {missing}"
            )

        valid_statuses = {
            "active",
            "paused",
            "completed",
            "stopped",
        }

        if result["status"] not in valid_statuses:
            raise RuntimeError(
                "Invalid follow-up status"
            )

        confidence = float(
            result["confidence"]
        )

        if confidence < 0 or confidence > 100:
            raise RuntimeError(
                "Follow-up confidence must be between 0 and 100"
            )

        return result

    async def _store_followup(
        self,
        prospect_id: str,
        campaign_id: str,
        conversation_id: str | None,
        result: dict[str, Any],
    ) -> dict[str, Any]:

        payload = {
            "prospect_id": prospect_id,
            "campaign_id": campaign_id,
            "conversation_id": conversation_id,
            "current_step": result["current_step"],
            "max_steps": result["max_steps"],
            "next_action_at": result["next_action_at"],
            "next_channel": result["next_channel"],
            "status": result["status"],
            "stop_reason": result["stop_reason"],
            "reasoning": result["reasoning"],
        }

        response = (
            supabase
            .table("followup_plans")
            .upsert(
                payload,
                on_conflict="prospect_id,campaign_id",
            )
            .execute()
        )

        if not response.data:
            raise RuntimeError(
                "Failed to store follow-up plan"
            )

        return response.data[0]