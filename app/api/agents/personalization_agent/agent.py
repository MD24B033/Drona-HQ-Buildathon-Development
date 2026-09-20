"""Personalization Agent.

Writes the actual outreach message for one prospect, grounded in that
prospect's research, ICP fit, outreach strategy and the campaign
knowledge base. The draft is recorded as an `outreach_events` row so the
Conversation Agent can pick it up and send it.
"""

import asyncio
import json
from typing import Any

from core.config import model_for
from core.gemini import clamp_score, generate_json
from core.runs import record_event
from db.supabase_client import supabase
from rag.retrieval import format_knowledge_context, retrieve_knowledge


REQUIRED_FIELDS = [
    "channel",
    "subject",
    "message",
    "personalization_angle",
    "personalization_points",
    "call_to_action",
    "evidence",
    "confidence",
]

VALID_CHANNELS = {"email", "linkedin", "sms", "voice"}


class PersonalizationAgent:

    agent_type = "personalization"

    def __init__(self, system_prompt: str | None = None):
        self.model = model_for("personalization")
        self.system_prompt = system_prompt

    async def run(
        self,
        prospect_id: str,
        icp_id: str | None = None,
        campaign_id: str | None = None,
    ) -> dict[str, Any]:
        """Draft a message for `prospect_id`.

        Either `icp_id` or `campaign_id` must be supplied; the ICP is
        used to resolve the campaign when only it is given.
        """

        if not icp_id and not campaign_id:
            raise ValueError(
                "Either icp_id or campaign_id must be provided."
            )

        context = await asyncio.to_thread(
            self._load_context,
            prospect_id,
            icp_id,
            campaign_id,
        )

        resolved_campaign_id = context["campaign"]["id"]

        rag_chunks = await retrieve_knowledge(
            campaign_id=resolved_campaign_id,
            query=self._build_rag_query(context),
        )

        result = await generate_json(
            model=self.model,
            prompt=self._build_prompt(
                context=context,
                rag_context=format_knowledge_context(rag_chunks),
            ),
            system_instruction=self.system_prompt,
        )

        personalization = self._normalize(result, context)

        event = await asyncio.to_thread(
            record_event,
            resolved_campaign_id,
            "message_drafted",
            "completed",
            personalization,
            prospect_id,
            self.agent_type,
            personalization["channel"],
        )

        return {
            "success": True,
            "agent": "personalization",
            "icp_id": context["icp"]["id"] if context["icp"] else None,
            "prospect_id": prospect_id,
            "campaign_id": resolved_campaign_id,
            "personalization": personalization,
            "event_id": event["id"] if event else None,
            "rag_chunks_used": len(rag_chunks),
        }

    # ========================================================
    # CONTEXT
    # ========================================================

    def _load_context(
        self,
        prospect_id: str,
        icp_id: str | None,
        campaign_id: str | None,
    ) -> dict[str, Any]:

        icp = None

        if icp_id:
            icp_response = (
                supabase
                .table("icps")
                .select("id, campaign_id, name, description, criteria")
                .eq("id", icp_id)
                .maybe_single()
                .execute()
            )

            icp = icp_response.data if icp_response else None

            if not icp:
                raise ValueError("ICP not found")

            campaign_id = icp["campaign_id"]

        prospect_response = (
            supabase
            .table("prospects")
            .select("*")
            .eq("id", prospect_id)
            .maybe_single()
            .execute()
        )

        prospect = prospect_response.data if prospect_response else None

        if not prospect:
            raise ValueError("Prospect not found")

        campaign_response = (
            supabase
            .table("campaigns")
            .select("*")
            .eq("id", campaign_id)
            .maybe_single()
            .execute()
        )

        campaign = campaign_response.data if campaign_response else None

        if not campaign:
            raise ValueError("Campaign not found")

        company = None

        if prospect.get("company_id"):
            company_response = (
                supabase
                .table("companies")
                .select("*")
                .eq("id", prospect["company_id"])
                .maybe_single()
                .execute()
            )

            company = company_response.data if company_response else None

        icp_match = self._best_icp_match(prospect_id, campaign_id, icp_id)

        # If no ICP was supplied, fall back to the one the prospect
        # actually matched inside this campaign.
        if not icp and icp_match and icp_match.get("icps"):
            icp = icp_match["icps"]

        research = self._maybe_single(
            "prospect_research", prospect_id, campaign_id
        )

        strategy = self._maybe_single(
            "outreach_strategies", prospect_id, campaign_id
        )

        return {
            "icp": icp,
            "campaign": campaign,
            "prospect": prospect,
            "company": company,
            "icp_match": icp_match,
            "research": research,
            "strategy": strategy,
        }

    def _best_icp_match(
        self,
        prospect_id: str,
        campaign_id: str,
        icp_id: str | None,
    ) -> dict[str, Any] | None:

        query = (
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
        )

        if icp_id:
            query = query.eq("icp_id", icp_id)

        response = (
            query
            .order("match_score", desc=True)
            .limit(1)
            .execute()
        )

        return response.data[0] if response.data else None

    def _maybe_single(
        self,
        table: str,
        prospect_id: str,
        campaign_id: str,
    ) -> dict[str, Any] | None:

        response = (
            supabase
            .table(table)
            .select("*")
            .eq("prospect_id", prospect_id)
            .eq("campaign_id", campaign_id)
            .maybe_single()
            .execute()
        )

        return response.data if response else None

    def _build_rag_query(self, context: dict[str, Any]) -> str:

        prospect = context["prospect"]
        company = context["company"]
        icp = context["icp"] or {}
        research = context["research"]

        parts = [
            f"ICP: {icp.get('name', '')}",
            f"ICP description: {icp.get('description', '')}",
            f"ICP criteria: {json.dumps(icp.get('criteria') or {})}",
            f"Prospect: {prospect.get('full_name', '')}",
            f"Title: {prospect.get('current_title', '')}",
            f"Functional area: {prospect.get('functional_area', '')}",
            "Expertise: "
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

        if research:
            parts.extend(
                [
                    f"Research summary: {research.get('summary', '')}",
                    "Pain points: "
                    f"{json.dumps(research.get('pain_points') or [])}",
                    "Buying signals: "
                    f"{json.dumps(research.get('buying_signals') or [])}",
                    "Technologies: "
                    f"{json.dumps(research.get('technologies') or [])}",
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

        def dump(key: str) -> str:
            return json.dumps(context[key], indent=2, default=str)

        return f"""
You are the Personalization Agent for a B2B sales automation system.

Your task is to create a highly personalized sales message for one
specific prospect.

Use ONLY the information provided below. Never invent facts. Never
assume company size, revenue, technologies, responsibilities,
achievements, business problems, buying intent, company initiatives,
personal interests, events, metrics, products, customers or results.

Missing information must remain missing.

Base the personalization on the strongest available combination of the
prospect, their company, the ICP criteria and fitment, the research, the
campaign objective and instructions, and the retrieved knowledge.

Do not mention the ICP, scoring, internal agents, RAG, the database or
any internal reasoning in the message. Do not make the message sound
like an AI-generated template. Keep it concise and suitable for a real
B2B sales interaction.

If an outreach strategy is supplied, write for its primary channel.

Return JSON only using this exact structure:

{{
    "channel": "email",
    "subject": "",
    "message": "",
    "personalization_angle": "",
    "personalization_points": [],
    "call_to_action": "",
    "evidence": [],
    "confidence": 0
}}

channel must be one of email, linkedin, sms, voice.
confidence must be a number from 0 to 100.

ICP:
{dump("icp")}

CAMPAIGN:
{dump("campaign")}

PROSPECT:
{dump("prospect")}

COMPANY:
{dump("company")}

ICP FITMENT:
{dump("icp_match")}

PROSPECT RESEARCH:
{dump("research")}

OUTREACH STRATEGY:
{dump("strategy")}

RELEVANT CAMPAIGN KNOWLEDGE:
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
            raise RuntimeError(
                f"Missing personalization fields: {missing}"
            )

        message = str(result.get("message") or "").strip()

        if not message:
            raise RuntimeError(
                "Generated personalization message is empty"
            )

        channel = result.get("channel")

        if channel not in VALID_CHANNELS:
            strategy = context.get("strategy") or {}

            channel = strategy.get("primary_channel") or "email"

        points = result.get("personalization_points")
        evidence = result.get("evidence")

        return {
            "channel": channel,
            "subject": str(result.get("subject") or "").strip(),
            "message": message,
            "personalization_angle": str(
                result.get("personalization_angle") or ""
            ).strip(),
            "personalization_points": (
                points if isinstance(points, list) else []
            ),
            "call_to_action": str(
                result.get("call_to_action") or ""
            ).strip(),
            "evidence": evidence if isinstance(evidence, list) else [],
            "confidence": clamp_score(result.get("confidence")),
        }


async def personalize_prospect(
    prospect_id: str,
    icp_id: str | None = None,
    campaign_id: str | None = None,
) -> dict[str, Any]:

    return await PersonalizationAgent().run(
        prospect_id=prospect_id,
        icp_id=icp_id,
        campaign_id=campaign_id,
    )
