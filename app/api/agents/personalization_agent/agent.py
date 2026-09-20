import json
import os
from typing import Any

from google import genai
from google.genai import types

from db.supabase_client import supabase


class PersonalizationAgent:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")

        self.client = genai.Client(api_key=api_key)

        self.model = os.getenv(
            "PERSONALIZATION_MODEL",
            "gemini-3.6-flash",
        )

        self.embedding_model = os.getenv(
            "EMBEDDING_MODEL",
            "gemini-embedding-001",
        )

        self.top_k = int(
            os.getenv("RAG_TOP_K", "8")
        )

        self.min_similarity = float(
            os.getenv("RAG_MIN_SIMILARITY", "0.35")
        )

    async def run(
        self,
        icp_id: str,
        prospect_id: str,
    ) -> dict[str, Any]:

        context = await self._load_context(
            icp_id=icp_id,
            prospect_id=prospect_id,
        )

        rag_context = await self._retrieve_rag(
            campaign_id=context["campaign"]["id"],
            context=context,
        )

        prompt = self._build_prompt(
            context=context,
            rag_context=rag_context,
        )

        result = await self._generate(prompt)

        return {
            "success": True,
            "agent": "personalization",
            "icp_id": icp_id,
            "prospect_id": prospect_id,
            "campaign_id": context["campaign"]["id"],
            "personalization": result,
            "rag": {
                "chunks_used": len(rag_context),
            },
        }

    async def _load_context(
        self,
        icp_id: str,
        prospect_id: str,
    ) -> dict[str, Any]:

        icp_response = (
            supabase
            .table("icps")
            .select(
                "id, campaign_id, name, description, criteria"
            )
            .eq("id", icp_id)
            .single()
            .execute()
        )

        icp = icp_response.data

        if not icp:
            raise ValueError("ICP not found")

        prospect_response = (
            supabase
            .table("prospects")
            .select(
                """
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
                """
            )
            .eq("id", prospect_id)
            .single()
            .execute()
        )

        prospect = prospect_response.data

        if not prospect:
            raise ValueError("Prospect not found")

        campaign_response = (
            supabase
            .table("campaigns")
            .select("*")
            .eq("id", icp["campaign_id"])
            .single()
            .execute()
        )

        campaign = campaign_response.data

        if not campaign:
            raise ValueError("Campaign not found")

        company = None

        if prospect.get("company_id"):
            company_response = (
                supabase
                .table("companies")
                .select(
                    """
                    id,
                    name,
                    website,
                    linkedin_url,
                    industry,
                    employee_count,
                    country,
                    city,
                    description,
                    context
                    """
                )
                .eq("id", prospect["company_id"])
                .single()
                .execute()
            )

            company = company_response.data

        icp_match = None

        try:
            match_response = (
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
                    evaluated_at
                    """
                )
                .eq("prospect_id", prospect_id)
                .eq("icp_id", icp_id)
                .maybe_single()
                .execute()
            )

            icp_match = match_response.data

        except Exception:
            icp_match = None

        research = None

        try:
            research_response = (
                supabase
                .table("prospect_research")
                .select("*")
                .eq("prospect_id", prospect_id)
                .eq("campaign_id", icp["campaign_id"])
                .maybe_single()
                .execute()
            )

            research = research_response.data

        except Exception:
            research = None

        strategy = None

        try:
            strategy_response = (
                supabase
                .table("outreach_strategies")
                .select("*")
                .eq("prospect_id", prospect_id)
                .eq("campaign_id", icp["campaign_id"])
                .maybe_single()
                .execute()
            )

            strategy = strategy_response.data

        except Exception:
            strategy = None

        return {
            "icp": icp,
            "campaign": campaign,
            "prospect": prospect,
            "company": company,
            "icp_match": icp_match,
            "research": research,
            "strategy": strategy,
        }

    async def _create_embedding(
        self,
        text: str,
    ) -> list[float]:

        response = await self.client.aio.models.embed_content(
            model=self.embedding_model,
            contents=text,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=768,
            ),
        )

        if not response.embeddings:
            raise RuntimeError(
                "Gemini returned no embedding"
            )

        return list(
            response.embeddings[0].values
        )

    async def _retrieve_rag(
        self,
        campaign_id: str,
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:

        prospect = context["prospect"]
        company = context["company"]
        icp = context["icp"]
        research = context["research"]

        query_parts = [
            f"ICP: {icp.get('name', '')}",
            f"ICP description: {icp.get('description', '')}",
            f"ICP criteria: {json.dumps(icp.get('criteria', {}))}",
            f"Prospect: {prospect.get('full_name', '')}",
            f"Title: {prospect.get('current_title', '')}",
            f"Functional area: {prospect.get('functional_area', '')}",
            f"Expertise: {json.dumps(prospect.get('areas_of_expertise', []))}",
        ]

        if company:
            query_parts.extend([
                f"Company: {company.get('name', '')}",
                f"Industry: {company.get('industry', '')}",
                f"Company description: {company.get('description', '')}",
            ])

        if research:
            query_parts.extend([
                f"Research summary: {research.get('summary', '')}",
                f"Pain points: {json.dumps(research.get('pain_points', []))}",
                f"Buying signals: {json.dumps(research.get('buying_signals', []))}",
                f"Technologies: {json.dumps(research.get('technologies', []))}",
            ])

        query = "\n".join(query_parts)

        embedding = await self._create_embedding(query)

        response = (
            supabase
            .rpc(
                "match_knowledge_chunks",
                {
                    "query_embedding": embedding,
                    "match_campaign_id": campaign_id,
                    "match_count": self.top_k,
                    "min_similarity": self.min_similarity,
                },
            )
            .execute()
        )

        return response.data or []

    def _build_prompt(
        self,
        context: dict[str, Any],
        rag_context: list[dict[str, Any]],
    ) -> str:

        rag_text = "\n\n".join(
            [
                (
                    f"Knowledge {index + 1} "
                    f"(similarity: {chunk.get('similarity', 0):.3f}):\n"
                    f"{chunk.get('content', '')}"
                )
                for index, chunk in enumerate(rag_context)
            ]
        )

        if not rag_text:
            rag_text = "No relevant campaign knowledge was found."

        return f"""
You are the Personalization Agent for a B2B sales automation system.

Your task is to create a highly personalized sales message for one specific prospect who is being evaluated against one specific ICP.

Use ONLY the information provided below.

Never invent facts.

Never assume:
- company size
- revenue
- technologies
- responsibilities
- achievements
- business problems
- buying intent
- company initiatives
- personal interests
- events
- metrics
- products
- customers
- results

Missing information must remain missing.

The goal is to produce a natural sales message that feels relevant to this specific prospect.

The personalization should be based on the strongest available combination of:
- prospect information
- company information
- ICP criteria
- ICP fitment
- research
- campaign objective
- campaign instructions
- campaign knowledge
- RAG context

Do not mention the ICP, scoring system, internal agent, RAG, database, or internal reasoning in the message.

Do not make the message sound like an AI-generated template.

Keep it concise and suitable for a real B2B sales interaction.

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

The confidence must be a number from 0 to 100.

ICP:
{json.dumps(context["icp"], indent=2, default=str)}

CAMPAIGN:
{json.dumps(context["campaign"], indent=2, default=str)}

PROSPECT:
{json.dumps(context["prospect"], indent=2, default=str)}

COMPANY:
{json.dumps(context["company"], indent=2, default=str)}

ICP FITMENT:
{json.dumps(context["icp_match"], indent=2, default=str)}

PROSPECT RESEARCH:
{json.dumps(context["research"], indent=2, default=str)}

OUTREACH STRATEGY:
{json.dumps(context["strategy"], indent=2, default=str)}

RELEVANT CAMPAIGN KNOWLEDGE:
{rag_text}
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
                "Gemini returned an empty response"
            )

        try:
            result = json.loads(response.text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Gemini returned invalid JSON"
            ) from exc

        if not isinstance(result, dict):
            raise RuntimeError(
                "Gemini returned an invalid response object"
            )

        required_fields = [
            "channel",
            "subject",
            "message",
            "personalization_angle",
            "personalization_points",
            "call_to_action",
            "evidence",
            "confidence",
        ]

        missing = [
            field
            for field in required_fields
            if field not in result
        ]

        if missing:
            raise RuntimeError(
                f"Missing personalization fields: {missing}"
            )

        confidence = float(
            result["confidence"]
        )

        if confidence < 0 or confidence > 100:
            raise RuntimeError(
                "Confidence must be between 0 and 100"
            )

        if not str(result["message"]).strip():
            raise RuntimeError(
                "Generated personalization message is empty"
            )

        return result


async def personalize_prospect(
    icp_id: str,
    prospect_id: str,
) -> dict[str, Any]:

    agent = PersonalizationAgent()

    return await agent.run(
        icp_id=icp_id,
        prospect_id=prospect_id,
    )