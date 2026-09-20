"""Prospect Research Agent.

Organises everything known about a prospect - their company, ICP fit and
the campaign knowledge base - into structured sales intelligence stored
in `prospect_research`.
"""

import asyncio
import json
from typing import Any

from core.config import model_for
from core.gemini import clamp_score, generate_json
from db.supabase_client import supabase
from rag.retrieval import format_knowledge_context, retrieve_knowledge


REQUIRED_FIELDS = [
    "summary",
    "company_summary",
    "role_summary",
    "pain_points",
    "buying_signals",
    "relevant_events",
    "technologies",
    "evidence",
    "confidence",
]

LIST_FIELDS = [
    "pain_points",
    "buying_signals",
    "relevant_events",
    "technologies",
    "evidence",
]


class ResearchAgent:

    agent_type = "research"

    def __init__(self, system_prompt: str | None = None):
        self.model = model_for("research")
        self.system_prompt = system_prompt

    async def run(
        self,
        prospect_id: str,
        campaign_id: str,
    ) -> dict[str, Any]:

        context = await self._load_context(prospect_id, campaign_id)

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

        normalized = self._normalize(result)

        stored = await asyncio.to_thread(
            self._store_research,
            prospect_id,
            campaign_id,
            normalized,
            context.get("previous_version", 0),
        )

        return {
            "success": True,
            "agent": "research",
            "prospect_id": prospect_id,
            "campaign_id": campaign_id,
            "research": stored,
            "rag_chunks_used": len(rag_chunks),
        }

    # ========================================================
    # CONTEXT
    # ========================================================

    async def _load_context(
        self,
        prospect_id: str,
        campaign_id: str,
    ) -> dict[str, Any]:

        return await asyncio.to_thread(
            self._load_context_sync,
            prospect_id,
            campaign_id,
        )

    def _load_context_sync(
        self,
        prospect_id: str,
        campaign_id: str,
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

        icp_match = (
            icp_response.data[0]
            if icp_response.data
            else None
        )

        previous = (
            supabase
            .table("prospect_research")
            .select("research_version")
            .eq("prospect_id", prospect_id)
            .eq("campaign_id", campaign_id)
            .maybe_single()
            .execute()
        )

        previous_version = 0

        if previous and previous.data:
            previous_version = previous.data.get("research_version") or 0

        return {
            "campaign": campaign.data,
            "prospect": prospect.data,
            "company": company,
            "icp_match": icp_match,
            "previous_version": previous_version,
        }

    def _build_rag_query(self, context: dict[str, Any]) -> str:

        prospect = context["prospect"]
        company = context["company"]
        campaign = context["campaign"]
        icp_match = context["icp_match"]

        parts = [
            f"Campaign objective: {campaign.get('objective', '')}",
            "Campaign knowledge: "
            f"{campaign.get('campaign_specific_knowledge', '')}",
            "Target personas: "
            f"{json.dumps(campaign.get('target_personas') or [])}",
            f"Prospect title: {prospect.get('current_title', '')}",
            f"Functional area: {prospect.get('functional_area', '')}",
            "Areas of expertise: "
            f"{json.dumps(prospect.get('areas_of_expertise') or [])}",
        ]

        if company:
            parts.extend(
                [
                    f"Company: {company.get('name', '')}",
                    f"Industry: {company.get('industry', '')}",
                    "Company description: "
                    f"{company.get('description', '')}",
                ]
            )

        if icp_match:
            parts.extend(
                [
                    "ICP: "
                    f"{json.dumps(icp_match.get('icps') or {}, default=str)}",
                    f"ICP reasoning: {icp_match.get('reasoning', '')}",
                ]
            )

        return "\n".join(parts)

    # ========================================================
    # PROMPT
    # ========================================================

    def _build_prompt(
        self,
        context: dict[str, Any],
        rag_context: str,
    ) -> str:

        campaign_json = json.dumps(
            context["campaign"], indent=2, default=str
        )
        prospect_json = json.dumps(
            context["prospect"], indent=2, default=str
        )
        company_json = json.dumps(
            context["company"], indent=2, default=str
        )
        icp_json = json.dumps(
            context["icp_match"], indent=2, default=str
        )

        return f"""
You are a B2B Prospect Research Agent.

Research the supplied prospect using ONLY the information provided.

Your job is to organise useful sales intelligence for later
personalization, strategy, conversation and follow-up.

Never invent facts. Do not assume revenue, employee count,
technologies, initiatives, buying intent, pain points, events,
responsibilities, achievements, company priorities or personal
interests.

If information is unavailable, leave it out rather than inventing it.

Return JSON only:

{{
    "summary": "",
    "company_summary": "",
    "role_summary": "",
    "pain_points": [],
    "buying_signals": [],
    "relevant_events": [],
    "technologies": [],
    "evidence": [],
    "confidence": 0
}}

confidence must be a number from 0 to 100.

Every important claim should be supported by supplied data or retrieved
campaign knowledge.

CAMPAIGN:
{campaign_json}

PROSPECT:
{prospect_json}

COMPANY:
{company_json}

ICP MATCH:
{icp_json}

RELEVANT CAMPAIGN KNOWLEDGE:
{rag_context}
"""

    # ========================================================
    # RESULT
    # ========================================================

    def _normalize(self, result: dict[str, Any]) -> dict[str, Any]:

        missing = [
            field
            for field in REQUIRED_FIELDS
            if field not in result
        ]

        if missing:
            raise RuntimeError(f"Missing research fields: {missing}")

        normalized = {
            "summary": str(result.get("summary") or ""),
            "company_summary": str(result.get("company_summary") or ""),
            "role_summary": str(result.get("role_summary") or ""),
            "confidence": clamp_score(result.get("confidence")),
        }

        for field in LIST_FIELDS:
            value = result.get(field)

            normalized[field] = value if isinstance(value, list) else []

        return normalized

    def _store_research(
        self,
        prospect_id: str,
        campaign_id: str,
        result: dict[str, Any],
        previous_version: int,
    ) -> dict[str, Any]:

        payload = {
            "prospect_id": prospect_id,
            "campaign_id": campaign_id,
            "research_version": previous_version + 1,
            **result,
        }

        response = (
            supabase
            .table("prospect_research")
            .upsert(payload, on_conflict="prospect_id,campaign_id")
            .execute()
        )

        if not response.data:
            raise RuntimeError("Failed to store prospect research")

        return response.data[0]


async def research_prospect(
    prospect_id: str,
    campaign_id: str,
) -> dict[str, Any]:

    return await ResearchAgent().run(
        prospect_id=prospect_id,
        campaign_id=campaign_id,
    )
