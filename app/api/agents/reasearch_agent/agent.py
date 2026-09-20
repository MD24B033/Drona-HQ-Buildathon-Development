import json
import os
from typing import Any

from google import genai
from google.genai import types

from db.supabase_client import supabase
from rag.retrieval import retrieve_knowledge, format_knowledge_context


class ResearchAgent:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")

        self.client = genai.Client(api_key=api_key)

        self.model = os.getenv(
            "RESEARCH_MODEL",
            "gemini-3.6-flash",
        )

    async def run(
        self,
        prospect_id: str,
        campaign_id: str,
    ) -> dict[str, Any]:

        context = await self._load_context(
            prospect_id,
            campaign_id,
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

        stored = await self._store_research(
            prospect_id=prospect_id,
            campaign_id=campaign_id,
            result=result,
        )

        return {
            "success": True,
            "agent": "research",
            "prospect_id": prospect_id,
            "campaign_id": campaign_id,
            "research": stored,
            "rag_chunks_used": len(rag_chunks),
        }

    async def _load_context(
        self,
        prospect_id: str,
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

        icp_response = (
            supabase
            .table("prospect_icp_matches")
            .select(
                """
                *,
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

        return {
            "campaign": campaign,
            "prospect": prospect,
            "company": company,
            "icp_match": icp_match,
        }

    def _build_rag_query(
        self,
        context: dict[str, Any],
    ) -> str:

        prospect = context["prospect"]
        company = context["company"]
        campaign = context["campaign"]
        icp_match = context["icp_match"]

        parts = [
            f"Campaign objective: {campaign.get('objective', '')}",
            f"Campaign knowledge: {campaign.get('campaign_specific_knowledge', '')}",
            f"Target personas: {json.dumps(campaign.get('target_personas', []))}",
            f"Prospect title: {prospect.get('current_title', '')}",
            f"Functional area: {prospect.get('functional_area', '')}",
            f"Areas of expertise: {json.dumps(prospect.get('areas_of_expertise', []))}",
        ]

        if company:
            parts.extend([
                f"Company: {company.get('name', '')}",
                f"Industry: {company.get('industry', '')}",
                f"Company description: {company.get('description', '')}",
            ])

        if icp_match:
            parts.extend([
                f"ICP: {json.dumps(icp_match.get('icps', {}), default=str)}",
                f"ICP reasoning: {icp_match.get('reasoning', '')}",
            ])

        return "\n".join(parts)

    def _build_prompt(
        self,
        context: dict[str, Any],
        rag_context: str,
    ) -> str:

        return f"""
You are a B2B Prospect Research Agent.

Research the supplied prospect using ONLY the information provided.

Your job is to organize useful sales intelligence for later personalization,
strategy, conversation and follow-up.

Never invent facts.

Do not assume:
- revenue
- employee count
- technologies
- initiatives
- buying intent
- pain points
- events
- responsibilities
- achievements
- company priorities
- personal interests

If information is unavailable, leave it unsupported rather than inventing it.

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

Every important claim should be supported by supplied data or retrieved
campaign knowledge.

CAMPAIGN:
{json.dumps(context["campaign"], indent=2, default=str)}

PROSPECT:
{json.dumps(context["prospect"], indent=2, default=str)}

COMPANY:
{json.dumps(context["company"], indent=2, default=str)}

ICP MATCH:
{json.dumps(context["icp_match"], indent=2, default=str)}

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
                "Gemini returned an empty research response"
            )

        result = json.loads(response.text)

        if not isinstance(result, dict):
            raise RuntimeError(
                "Invalid research response"
            )

        required = [
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

        missing = [
            field
            for field in required
            if field not in result
        ]

        if missing:
            raise RuntimeError(
                f"Missing research fields: {missing}"
            )

        confidence = float(
            result["confidence"]
        )

        if confidence < 0 or confidence > 100:
            raise RuntimeError(
                "Research confidence must be between 0 and 100"
            )

        return result

    async def _store_research(
        self,
        prospect_id: str,
        campaign_id: str,
        result: dict[str, Any],
    ) -> dict[str, Any]:

        payload = {
            "prospect_id": prospect_id,
            "campaign_id": campaign_id,
            "summary": result["summary"],
            "company_summary": result["company_summary"],
            "role_summary": result["role_summary"],
            "pain_points": result["pain_points"],
            "buying_signals": result["buying_signals"],
            "relevant_events": result["relevant_events"],
            "technologies": result["technologies"],
            "evidence": result["evidence"],
            "confidence": result["confidence"],
        }

        response = (
            supabase
            .table("prospect_research")
            .upsert(
                payload,
                on_conflict="prospect_id,campaign_id",
            )
            .execute()
        )

        if not response.data:
            raise RuntimeError(
                "Failed to store prospect research"
            )

        return response.data[0]