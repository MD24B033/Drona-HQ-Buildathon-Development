"""Prospect Discovery Agent.

Finds real people at a target company who look relevant to an ICP,
writes them to `prospects`, and optionally hands each one to the ICP
Fitment Agent.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from core.config import DISCOVERY_MAX_CANDIDATES, model_for
from core.gemini import client as gemini, parse_json_object
from db.supabase_client import supabase

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """
You are a Prospect Discovery Agent for a B2B sales platform.

Your job is to find REAL PEOPLE who work at a SPECIFIC COMPANY and
appear relevant to a specific Ideal Customer Profile (ICP).

You are NOT the final ICP qualification agent. Your task is discovery.

Search the web to find potential people at the company who match the
ICP's person-level requirements.

IMPORTANT RULES:

- Only return real people who have credible evidence of working at the
  specified company.
- Do not invent people, job titles, LinkedIn URLs or geography.
- Do not assume someone works at the company merely because their name
  appears in an unrelated article.
- Prefer official company pages, public professional profiles,
  conference speaker pages and reputable publications.
- If you cannot verify a field, return null for it.
- Never fabricate missing information.

ICP INTERPRETATION:

Pay particular attention to target job titles, seniority, functional
area, geography, expertise, company characteristics, and any explicit
inclusion or exclusion criteria.

Do NOT perform the final qualification decision. A candidate may be
returned even when some information is missing, provided there is
credible evidence that the person works at the company.

Return only structured candidate data. Do not write outreach messages
or sales copy.

Return JSON only, in exactly this shape:

{
  "candidates": [
    {
      "full_name": "",
      "current_title": null,
      "linkedin_url": null,
      "country": null,
      "city": null,
      "functional_area": null,
      "areas_of_expertise": [],
      "reasoning": "",
      "evidence": {},
      "sources": []
    }
  ]
}
"""


# ============================================================
# DATA ACCESS
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
        .maybe_single()
        .execute()
    )

    if not response or not response.data:
        raise ValueError(f"Company not found: {company_id}")

    return response.data


def fetch_icp(icp_id: str) -> dict[str, Any]:

    response = (
        supabase
        .table("icps")
        .select("id, campaign_id, name, description, criteria")
        .eq("id", icp_id)
        .maybe_single()
        .execute()
    )

    if not response or not response.data:
        raise ValueError(f"ICP not found: {icp_id}")

    return response.data


def fetch_campaign(campaign_id: str) -> dict[str, Any]:
    """Load the campaign columns that steer discovery.

    Note: the campaign itself has no `icp` column - ICPs live in their
    own table and are passed in separately.
    """

    response = (
        supabase
        .table("campaigns")
        .select(
            """
            id,
            profile_id,
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
        .maybe_single()
        .execute()
    )

    if not response or not response.data:
        raise ValueError(f"Campaign not found: {campaign_id}")

    return response.data


# ============================================================
# GEMINI DISCOVERY
# ============================================================

def build_prompt(
    company: dict[str, Any],
    icp: dict[str, Any],
    campaign: dict[str, Any],
) -> str:

    company_json = json.dumps(company, indent=2, default=str)
    icp_json = json.dumps(icp, indent=2, default=str)
    campaign_json = json.dumps(campaign, indent=2, default=str)

    return f"""
Find potential prospects at the following company who are relevant to
the supplied ICP.

========================
COMPANY
========================

{company_json}

========================
ICP
========================

{icp_json}

========================
CAMPAIGN
========================

{campaign_json}

========================
DISCOVERY REQUIREMENTS
========================

Find people who appear to match the ICP's target personas. Search for
current employees, their current job title, seniority, functional area,
public professional profile, relevant expertise and geography.

Prioritise people with strong evidence of being current employees of
this company.

Return up to {DISCOVERY_MAX_CANDIDATES} strong candidates. Do not return
generic employees merely because they work there.

For every candidate provide: full_name, current_title, linkedin_url if
verified, country if verified, city if verified, functional_area,
areas_of_expertise, reasoning, evidence and sources.

Again: DO NOT invent information. Return JSON only.
"""


async def discover_with_gemini(
    company: dict[str, Any],
    icp: dict[str, Any],
    campaign: dict[str, Any],
) -> list[dict[str, Any]]:
    """Ask Gemini, with Google Search grounding, for candidate people."""

    prompt = build_prompt(company=company, icp=icp, campaign=campaign)

    response = await gemini.aio.models.generate_content(
        model=model_for("prospect_discovery"),
        contents=SYSTEM_PROMPT + "\n\n" + prompt,
        config={
            # Grounded calls cannot also force a JSON mime type, so the
            # JSON object is parsed out of the text response.
            "tools": [{"google_search": {}}],
        },
    )

    if not response.text:
        raise RuntimeError("Gemini returned an empty discovery response")

    result = parse_json_object(response.text)

    candidates = result.get("candidates")

    if not isinstance(candidates, list):
        return []

    return [
        normalize_candidate(candidate)
        for candidate in candidates
        if isinstance(candidate, dict)
        and str(candidate.get("full_name") or "").strip()
    ][:DISCOVERY_MAX_CANDIDATES]


def normalize_candidate(candidate: dict[str, Any]) -> dict[str, Any]:

    def text(key: str) -> str | None:
        value = candidate.get(key)

        if value is None:
            return None

        value = str(value).strip()

        return value or None

    expertise = candidate.get("areas_of_expertise")

    if not isinstance(expertise, list):
        expertise = []

    evidence = candidate.get("evidence")

    if not isinstance(evidence, dict):
        evidence = {"notes": evidence} if evidence else {}

    sources = candidate.get("sources")

    if not isinstance(sources, list):
        sources = []

    return {
        "full_name": str(candidate.get("full_name")).strip(),
        "current_title": text("current_title"),
        "linkedin_url": text("linkedin_url"),
        "country": text("country"),
        "city": text("city"),
        "functional_area": text("functional_area"),
        "areas_of_expertise": [
            str(item).strip()
            for item in expertise
            if str(item).strip()
        ],
        "reasoning": text("reasoning") or "",
        "evidence": evidence,
        "sources": [str(item) for item in sources],
    }


# ============================================================
# PERSISTENCE
# ============================================================

def find_existing_prospect(
    company_id: str,
    candidate: dict[str, Any],
) -> dict[str, Any] | None:
    """LinkedIn is the strongest dedup key; fall back to company + name."""

    if candidate.get("linkedin_url"):

        response = (
            supabase
            .table("prospects")
            .select("*")
            .eq("linkedin_url", candidate["linkedin_url"])
            .limit(1)
            .execute()
        )

        if response.data:
            return response.data[0]

    response = (
        supabase
        .table("prospects")
        .select("*")
        .eq("company_id", company_id)
        .eq("full_name", candidate["full_name"])
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


def save_prospect(
    company_id: str,
    candidate: dict[str, Any],
) -> dict[str, Any]:

    existing = find_existing_prospect(
        company_id=company_id,
        candidate=candidate,
    )

    discovery_context = {
        "reasoning": candidate["reasoning"],
        "evidence": candidate["evidence"],
        "sources": candidate["sources"],
    }

    payload = {
        "company_id": company_id,
        "full_name": candidate["full_name"],
        "current_title": candidate["current_title"],
        "linkedin_url": candidate["linkedin_url"],
        "country": candidate["country"],
        "city": candidate["city"],
        "functional_area": candidate["functional_area"],
        "areas_of_expertise": candidate["areas_of_expertise"],
        "context": {"discovery": discovery_context},
    }

    if existing:
        # Preserve anything already stored alongside the discovery notes.
        old_context = existing.get("context")

        if not isinstance(old_context, dict):
            old_context = {}

        old_context["discovery"] = discovery_context

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
            f"Failed to save prospect: {candidate['full_name']}"
        )

    return response.data[0]


# ============================================================
# PIPELINE
# ============================================================

async def run_prospect_discovery(
    company_id: str,
    icp_id: str,
    run_fitment: bool = True,
) -> dict[str, Any]:

    logger.info(
        "Starting prospect discovery company=%s icp=%s",
        company_id,
        icp_id,
    )

    company = await asyncio.to_thread(fetch_company, company_id)

    icp = await asyncio.to_thread(fetch_icp, icp_id)

    campaign = await asyncio.to_thread(
        fetch_campaign,
        icp["campaign_id"],
    )

    candidates = await discover_with_gemini(
        company=company,
        icp=icp,
        campaign=campaign,
    )

    saved_prospects: list[dict[str, Any]] = []

    for candidate in candidates:

        try:
            prospect = await asyncio.to_thread(
                save_prospect,
                company_id,
                candidate,
            )

            saved_prospects.append(
                {
                    "prospect": prospect,
                    "candidate": candidate,
                }
            )

        except Exception:
            logger.exception(
                "Failed to save discovered prospect %s",
                candidate.get("full_name"),
            )

    fitment_results: list[dict[str, Any]] = []

    if run_fitment and saved_prospects:

        # Imported here to avoid a circular import at module load time.
        from agents.ICP_fitment.agent import ICPFitmentAgent

        fitment_agent = ICPFitmentAgent()

        for item in saved_prospects:

            prospect_id = item["prospect"]["id"]

            try:
                result = await fitment_agent.evaluate_one(
                    prospect_id=prospect_id,
                    icp_id=icp_id,
                )

                fitment_results.append(
                    {
                        "prospect_id": prospect_id,
                        "result": result,
                    }
                )

            except Exception as exc:
                logger.exception(
                    "ICP fitment failed prospect=%s icp=%s",
                    prospect_id,
                    icp_id,
                )

                fitment_results.append(
                    {
                        "prospect_id": prospect_id,
                        "error": str(exc),
                    }
                )

    return {
        "company_id": company_id,
        "icp_id": icp_id,
        "campaign_id": icp["campaign_id"],
        "company_name": company["name"],
        "discovered_count": len(candidates),
        "saved_count": len(saved_prospects),
        "fitment_count": len(fitment_results),
        "prospects": saved_prospects,
        "fitment": fitment_results,
    }


async def run_prospect_discovery_batch(
    company_ids: list[str],
    icp_id: str,
    run_fitment: bool = True,
) -> list[dict[str, Any]]:

    results: list[dict[str, Any]] = []

    for company_id in company_ids:

        try:
            results.append(
                await run_prospect_discovery(
                    company_id=company_id,
                    icp_id=icp_id,
                    run_fitment=run_fitment,
                )
            )

        except Exception as exc:
            logger.exception(
                "Prospect discovery failed company=%s icp=%s",
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
