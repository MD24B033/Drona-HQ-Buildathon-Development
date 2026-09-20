from __future__ import annotations

import logging
import os
from typing import Any

from google import genai
from pydantic import BaseModel, Field

from supabase.client import supabase
from icp_fitment import run_icp_fitment

logger = logging.getLogger(__name__)


# ============================================================
# CONFIG
# ============================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3-flash-preview",
)

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not configured")

gemini = genai.Client(api_key=GEMINI_API_KEY)


# ============================================================
# OUTPUT SCHEMAS
# ============================================================

class ProspectCandidate(BaseModel):
    full_name: str = Field(
        description="Full name of the person."
    )

    current_title: str | None = Field(
        default=None,
        description="Current professional job title."
    )

    linkedin_url: str | None = Field(
        default=None,
        description="Public LinkedIn profile URL if found."
    )

    country: str | None = None

    city: str | None = None

    functional_area: str | None = Field(
        default=None,
        description="Functional area such as Engineering, Product, Sales, Finance."
    )

    areas_of_expertise: list[str] = Field(
        default_factory=list
    )

    reasoning: str = Field(
        description="Why this person appears relevant to the ICP."
    )

    evidence: dict[str, Any] = Field(
        default_factory=dict,
        description="Evidence supporting the candidate."
    )

    sources: list[str] = Field(
        default_factory=list,
        description="URLs supporting the candidate."
    )


class ProspectDiscoveryResult(BaseModel):
    candidates: list[ProspectCandidate] = Field(
        default_factory=list
    )


# ============================================================
# PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are a Prospect Discovery Agent for a B2B sales platform.

Your job is to find REAL PEOPLE who work at a SPECIFIC COMPANY
and appear relevant to a specific Ideal Customer Profile (ICP).

You are NOT the final ICP qualification agent.

Your task is discovery.

INPUTS:

1. Company information
2. ICP information

You must search the web to find potential people at the company
who match the ICP's person-level requirements.

IMPORTANT RULES:

- Only return real people who have credible evidence of working
  at the specified company.
- Do not invent people.
- Do not invent job titles.
- Do not invent LinkedIn URLs.
- Do not invent geography.
- Do not assume someone works at the company merely because
  their name appears in an unrelated article.
- Prefer official company pages, public professional profiles,
  conference speaker pages, reputable publications, and other
  credible sources.
- LinkedIn URLs may be returned only when you actually find
  evidence for that profile.
- If you cannot verify a LinkedIn URL, return null.
- If you cannot verify a field, return null.
- Never fabricate missing information.

ICP INTERPRETATION:

Use the ICP to identify relevant people.

Pay particular attention to:

- target job titles
- seniority
- functional area
- geography
- expertise
- company characteristics
- explicit inclusion criteria
- explicit exclusions

Do NOT perform the final qualification decision.

A candidate can be returned even if some information is missing,
provided there is credible evidence that the person works at the
company and may fit the ICP.

Return only structured candidate data.
Do not write outreach messages.
Do not write sales copy.
"""


# ============================================================
# HELPERS
# ============================================================

def fetch_company(company_id: str) -> dict[str, Any]:
    response = (
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
        .eq("id", company_id)
        .single()
        .execute()
    )

    if not response.data:
        raise ValueError(
            f"Company not found: {company_id}"
        )

    return response.data


def fetch_icp(icp_id: str) -> dict[str, Any]:
    response = (
        supabase
        .table("icps")
        .select(
            """
            id,
            campaign_id,
            name,
            description,
            criteria
            """
        )
        .eq("id", icp_id)
        .single()
        .execute()
    )

    if not response.data:
        raise ValueError(
            f"ICP not found: {icp_id}"
        )

    return response.data


def fetch_campaign(campaign_id: str) -> dict[str, Any]:
    response = (
        supabase
        .table("campaigns")
        .select(
            """
            id,
            profile_id,
            icp,
            geography,
            target_personas,
            objective,
            prompts,
            agent_instructions,
            campaign_specific_knowledge,
            outreach_strategy,
            qualification_criteria,
            channel_configuration,
            daily_limits,
            human_approval_rules
            """
        )
        .eq("id", campaign_id)
        .single()
        .execute()
    )

    if not response.data:
        raise ValueError(
            f"Campaign not found: {campaign_id}"
        )

    return response.data


def build_prompt(
    company: dict[str, Any],
    icp: dict[str, Any],
    campaign: dict[str, Any],
) -> str:

    return f"""
Find potential prospects at the following company who are relevant
to the supplied ICP.

========================
COMPANY
========================

{company}

========================
ICP
========================

{icp}

========================
CAMPAIGN
========================

{campaign}

========================
DISCOVERY REQUIREMENTS
========================

Find people who appear to match the ICP's target personas.

Search for:

- current employees
- current job title
- seniority
- functional area
- public professional profile
- relevant expertise
- geography where relevant

Prioritize people who have strong evidence of being current
employees of this company.

Return up to 20 strong candidate prospects.

Do not return generic employees merely because they work there.

For every candidate provide:

- full_name
- current_title
- linkedin_url if verified
- country if verified
- city if verified
- functional_area
- areas_of_expertise
- reasoning
- evidence
- sources

Again:

DO NOT invent information.
"""


# ============================================================
# GEMINI DISCOVERY
# ============================================================

def discover_with_gemini(
    company: dict[str, Any],
    icp: dict[str, Any],
    campaign: dict[str, Any],
) -> ProspectDiscoveryResult:

    prompt = build_prompt(
        company=company,
        icp=icp,
        campaign=campaign,
    )

    response = gemini.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            {
                "role": "user",
                "parts": [
                    {
                        "text": (
                            SYSTEM_PROMPT
                            + "\n\n"
                            + prompt
                        )
                    }
                ],
            }
        ],
        config={
            "response_mime_type": "application/json",
            "response_schema": ProspectDiscoveryResult,

            # Gemini uses Google Search grounding to find
            # current public information.
            "tools": [
                {
                    "google_search": {}
                }
            ],
        },
    )

    if not response.text:
        raise RuntimeError(
            "Gemini returned an empty response"
        )

    return ProspectDiscoveryResult.model_validate_json(
        response.text
    )


# ============================================================
# EXISTING PROSPECT LOOKUP
# ============================================================

def find_existing_prospect(
    company_id: str,
    candidate: ProspectCandidate,
) -> dict[str, Any] | None:

    # LinkedIn is the strongest deduplication key.
    if candidate.linkedin_url:

        response = (
            supabase
            .table("prospects")
            .select("*")
            .eq(
                "linkedin_url",
                candidate.linkedin_url,
            )
            .limit(1)
            .execute()
        )

        if response.data:
            return response.data[0]

    # Fallback to company + full name.
    response = (
        supabase
        .table("prospects")
        .select("*")
        .eq("company_id", company_id)
        .eq("full_name", candidate.full_name)
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


# ============================================================
# UPSERT PROSPECT
# ============================================================

def save_prospect(
    company_id: str,
    candidate: ProspectCandidate,
) -> dict[str, Any]:

    existing = find_existing_prospect(
        company_id=company_id,
        candidate=candidate,
    )

    payload = {
        "company_id": company_id,
        "full_name": candidate.full_name,
        "current_title": candidate.current_title,
        "linkedin_url": candidate.linkedin_url,
        "country": candidate.country,
        "city": candidate.city,
        "functional_area": candidate.functional_area,
        "areas_of_expertise": candidate.areas_of_expertise,
        "context": {
            "discovery": {
                "reasoning": candidate.reasoning,
                "evidence": candidate.evidence,
                "sources": candidate.sources,
            }
        },
    }

    if existing:

        # Preserve existing context where possible.
        old_context = existing.get("context") or {}

        if not isinstance(old_context, dict):
            old_context = {}

        old_context["discovery"] = {
            "reasoning": candidate.reasoning,
            "evidence": candidate.evidence,
            "sources": candidate.sources,
        }

        payload["context"] = old_context

        response = (
            supabase
            .table("prospects")
            .update(payload)
            .eq("id", existing["id"])
            .execute()
        )

    else:

        response = (
            supabase
            .table("prospects")
            .insert(payload)
            .execute()
        )

    if not response.data:
        raise RuntimeError(
            f"Failed to save prospect: "
            f"{candidate.full_name}"
        )

    return response.data[0]


# ============================================================
# SAVE DISCOVERY STATUS
# ============================================================

def mark_discovery_status(
    prospect_id: str,
    icp_id: str,
    status: str,
    reasoning: str | None = None,
) -> None:

    # We don't create an ICP match here unless fitment runs.
    # This function is optional and can be removed if you don't
    # want discovery state stored in prospect_icp_matches.

    payload = {
        "status": status,
    }

    if reasoning:
        payload["reasoning"] = reasoning

    (
        supabase
        .table("prospect_icp_matches")
        .update(payload)
        .eq("prospect_id", prospect_id)
        .eq("icp_id", icp_id)
        .execute()
    )


# ============================================================
# FULL DISCOVERY PIPELINE
# ============================================================

def run_prospect_discovery(
    company_id: str,
    icp_id: str,
    run_fitment: bool = True,
) -> dict[str, Any]:

    logger.info(
        "Starting prospect discovery company=%s icp=%s",
        company_id,
        icp_id,
    )

    # ----------------------------------------
    # 1. Fetch company
    # ----------------------------------------

    company = fetch_company(company_id)

    # ----------------------------------------
    # 2. Fetch ICP
    # ----------------------------------------

    icp = fetch_icp(icp_id)

    # ----------------------------------------
    # 3. Fetch campaign
    # ----------------------------------------

    campaign = fetch_campaign(
        icp["campaign_id"]
    )

    # ----------------------------------------
    # 4. Discover people
    # ----------------------------------------

    discovery_result = discover_with_gemini(
        company=company,
        icp=icp,
        campaign=campaign,
    )

    saved_prospects = []

    # ----------------------------------------
    # 5. Save prospects
    # ----------------------------------------

    for candidate in discovery_result.candidates:

        try:

            prospect = save_prospect(
                company_id=company_id,
                candidate=candidate,
            )

            saved_prospects.append(
                {
                    "prospect": prospect,
                    "candidate": candidate.model_dump(),
                }
            )

        except Exception:
            logger.exception(
                "Failed to save discovered prospect %s",
                candidate.full_name,
            )

    # ----------------------------------------
    # 6. Run ICP fitment
    # ----------------------------------------

    fitment_results = []

    if run_fitment:

        for item in saved_prospects:

            prospect_id = item["prospect"]["id"]

            try:

                fitment = run_icp_fitment(
                    prospect_id=prospect_id,
                    icp_id=icp_id,
                )

                fitment_results.append(
                    {
                        "prospect_id": prospect_id,
                        "result": fitment,
                    }
                )

            except Exception:

                logger.exception(
                    "ICP fitment failed "
                    "prospect=%s icp=%s",
                    prospect_id,
                    icp_id,
                )

                fitment_results.append(
                    {
                        "prospect_id": prospect_id,
                        "error": "ICP fitment failed",
                    }
                )

    return {
        "company_id": company_id,
        "icp_id": icp_id,
        "company_name": company["name"],
        "discovered_count": len(
            discovery_result.candidates
        ),
        "saved_count": len(saved_prospects),
        "fitment_count": len(fitment_results),
        "prospects": saved_prospects,
        "fitment": fitment_results,
    }


# ============================================================
# BATCH DISCOVERY
# ============================================================

def run_prospect_discovery_batch(
    company_ids: list[str],
    icp_id: str,
    run_fitment: bool = True,
) -> list[dict[str, Any]]:

    results = []

    for company_id in company_ids:

        try:

            result = run_prospect_discovery(
                company_id=company_id,
                icp_id=icp_id,
                run_fitment=run_fitment,
            )

            results.append(result)

        except Exception as exc:

            logger.exception(
                "Prospect discovery failed "
                "company=%s icp=%s",
                company_id,
                icp_id,
            )

            results.append(
                {
                    "company_id": company_id,
                    "icp_id": icp_id,
                    "error": str(exc),
                }
            )

    return results