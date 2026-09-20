"""ICP Fitment Agent.

Scores prospects belonging to a campaign's target companies against one
ICP and writes the verdicts to `prospect_icp_matches`.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from core.config import (
    ICP_FITMENT_BATCH_SIZE,
    ICP_FITMENT_CONCURRENCY,
    ICP_FITMENT_MAX_RETRIES,
    ICP_FITMENT_RETRY_DELAY,
    model_for,
)
from core.gemini import clamp_score, generate_json, is_permanent_error
from db.supabase_client import supabase


SYSTEM_PROMPT = """
You are an ICP Fitment Agent for a B2B sales automation system.

Your job is to determine how well a prospect matches an Ideal Customer
Profile (ICP).

Evaluate ONLY information explicitly provided in:

1. The ICP name
2. The ICP description
3. The ICP criteria
4. The prospect data
5. The prospect's company context, when provided

Do not invent facts about the prospect or company.
Do not assume information that is missing.
Do not use outside knowledge.

You must return structured JSON with exactly these fields:

{
  "match_score": 0,
  "confidence": 0,
  "decision": "qualified",
  "reasoning": "",
  "evidence": {}
}

match_score: 0-100, how strongly the prospect matches the ICP.
confidence: 0-100, how confident you are given the available evidence.
decision: exactly one of qualified, disqualified, needs_review.
reasoning: a concise explanation of the score and decision.
evidence: an object of concrete evidence drawn from the supplied data.

Scoring:

90-100  Very strong match; the most important criteria are clearly met.
70-89   Strong match; most important criteria met, minor uncertainty.
50-69   Partial match; meaningful information missing or conflicting.
0-49    Poor match; strong evidence of a mismatch.

Decisions:

qualified      Strong evidence the prospect matches the important criteria.
disqualified   Strong evidence the prospect does not match them.
needs_review   Information is missing, ambiguous or contradictory.

Important rules:

- Never invent company size, industry, revenue, technology usage,
  geography, responsibilities, seniority, or any other characteristic.
- Missing information is NOT negative evidence; it reduces confidence.
- Evaluate the actual ICP criteria, not generic assumptions.
- Evidence must come from the supplied data.
- Return JSON only.
"""


DECISIONS = {"qualified", "disqualified", "needs_review"}


class ICPFitmentAgent:

    agent_type = "icp_fitment"

    def __init__(self, system_prompt: str | None = None):
        self.model = model_for("icp_fitment")
        self.system_prompt = system_prompt or SYSTEM_PROMPT
        self.semaphore = asyncio.Semaphore(ICP_FITMENT_CONCURRENCY)

    # ========================================================
    # MAIN PIPELINE
    # ========================================================

    async def run(
        self,
        icp_id: str,
        company_ids: list[str] | None = None,
        prospect_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Evaluate prospects against one ICP.

        ICP -> campaign -> campaign_companies -> prospects -> Gemini
        -> prospect_icp_matches.

        `company_ids` narrows the campaign's companies; `prospect_ids`
        restricts the run to specific people.
        """

        icp = await asyncio.to_thread(self.get_icp, icp_id)

        if not icp:
            raise ValueError(f"ICP {icp_id} not found.")

        campaign_id = icp.get("campaign_id")

        if not campaign_id:
            raise ValueError(
                f"ICP {icp_id} is not associated with a campaign."
            )

        campaign_company_ids = await asyncio.to_thread(
            self.get_campaign_company_ids,
            campaign_id,
        )

        if company_ids:
            requested = set(company_ids)

            selected_company_ids = [
                company_id
                for company_id in campaign_company_ids
                if company_id in requested
            ]
        else:
            selected_company_ids = campaign_company_ids

        empty_summary = {
            "icp_id": icp_id,
            "campaign_id": campaign_id,
            "company_ids": selected_company_ids,
            "total_companies": len(selected_company_ids),
            "total_prospects": 0,
            "processed": 0,
            "failed": 0,
            "qualified": 0,
            "disqualified": 0,
            "needs_review": 0,
        }

        if not selected_company_ids:
            return empty_summary

        prospects = await asyncio.to_thread(
            self.get_prospects,
            selected_company_ids,
            prospect_ids,
        )

        total_prospects = len(prospects)

        if total_prospects == 0:
            return empty_summary

        all_results: list[dict[str, Any]] = []

        processed = 0
        failed = 0

        for batch_start in range(
            0,
            total_prospects,
            ICP_FITMENT_BATCH_SIZE,
        ):

            batch = prospects[
                batch_start:batch_start + ICP_FITMENT_BATCH_SIZE
            ]

            print(
                "[ICP FITMENT] Processing prospects "
                f"{batch_start + 1}-{batch_start + len(batch)} "
                f"of {total_prospects}"
            )

            batch_results = await asyncio.gather(
                *[
                    self.evaluate_prospect(prospect=prospect, icp=icp)
                    for prospect in batch
                ],
                return_exceptions=True,
            )

            valid_results: list[dict[str, Any]] = []

            for result in batch_results:

                if isinstance(result, Exception) or result is None:
                    failed += 1

                    if isinstance(result, Exception):
                        print(
                            "[ICP FITMENT] Unexpected evaluation error:",
                            result,
                        )

                    continue

                valid_results.append(result)

                if result["status"] == "failed":
                    failed += 1
                else:
                    processed += 1

            if valid_results:
                await asyncio.to_thread(self.save_results, valid_results)

                all_results.extend(valid_results)

            print(
                "[ICP FITMENT] Batch complete | "
                f"processed={processed} | failed={failed}"
            )

        return self.build_summary(
            icp_id=icp_id,
            campaign_id=campaign_id,
            company_ids=selected_company_ids,
            results=all_results,
            total=total_prospects,
            failed=failed,
        )

    async def evaluate_one(
        self,
        prospect_id: str,
        icp_id: str,
    ) -> dict[str, Any]:
        """Score a single prospect. Used by the discovery agent."""

        icp = await asyncio.to_thread(self.get_icp, icp_id)

        if not icp:
            raise ValueError(f"ICP {icp_id} not found.")

        prospect = await asyncio.to_thread(
            self.get_prospect,
            prospect_id,
        )

        if not prospect:
            raise ValueError(f"Prospect {prospect_id} not found.")

        result = await self.evaluate_prospect(prospect=prospect, icp=icp)

        await asyncio.to_thread(self.save_results, [result])

        return result

    # ========================================================
    # DATA ACCESS
    # ========================================================

    PROSPECT_SELECT = """
        id,
        company_id,
        full_name,
        current_title,
        linkedin_url,
        country,
        city,
        functional_area,
        areas_of_expertise,
        context,
        companies (
            id,
            name,
            website,
            industry,
            employee_count,
            country,
            city,
            description,
            context
        )
    """

    def get_icp(self, icp_id: str) -> dict | None:

        response = (
            supabase
            .table("icps")
            .select("id, campaign_id, name, description, criteria")
            .eq("id", icp_id)
            .maybe_single()
            .execute()
        )

        return response.data if response else None

    def get_campaign_company_ids(self, campaign_id: str) -> list[str]:

        response = (
            supabase
            .table("campaign_companies")
            .select("company_id")
            .eq("campaign_id", campaign_id)
            .execute()
        )

        return [
            row["company_id"]
            for row in (response.data or [])
            if row.get("company_id")
        ]

    def get_prospect(self, prospect_id: str) -> dict | None:

        response = (
            supabase
            .table("prospects")
            .select(self.PROSPECT_SELECT)
            .eq("id", prospect_id)
            .maybe_single()
            .execute()
        )

        return response.data if response else None

    def get_prospects(
        self,
        company_ids: list[str],
        prospect_ids: list[str] | None = None,
    ) -> list[dict]:

        if not company_ids:
            return []

        query = (
            supabase
            .table("prospects")
            .select(self.PROSPECT_SELECT)
            .in_("company_id", company_ids)
        )

        if prospect_ids:
            query = query.in_("id", prospect_ids)

        response = query.execute()

        return response.data or []

    # ========================================================
    # EVALUATION
    # ========================================================

    async def evaluate_prospect(
        self,
        prospect: dict,
        icp: dict,
    ) -> dict[str, Any]:

        async with self.semaphore:

            prompt = self.build_prompt(prospect=prospect, icp=icp)

            try:
                result = await generate_json(
                    model=self.model,
                    prompt=prompt,
                    system_instruction=self.system_prompt,
                    max_retries=ICP_FITMENT_MAX_RETRIES,
                    retry_delay=ICP_FITMENT_RETRY_DELAY,
                )

                return self.normalize_result(
                    result=result,
                    prospect=prospect,
                    icp=icp,
                )

            except Exception as exc:
                print(
                    "[ICP FITMENT] Failed prospect "
                    f"{prospect.get('id')}: {exc}"
                )

                if is_permanent_error(exc):
                    print(
                        "[ICP FITMENT] Permanent error - check "
                        "GEMINI_API_KEY and the configured model name."
                    )

                return self.build_failed_result(
                    prospect=prospect,
                    icp=icp,
                    error=str(exc),
                )

    def build_prompt(self, prospect: dict, icp: dict) -> str:

        company = prospect.get("companies") or {}

        prospect_data = {
            "full_name": prospect.get("full_name"),
            "current_title": prospect.get("current_title"),
            "linkedin_url": prospect.get("linkedin_url"),
            "country": prospect.get("country"),
            "city": prospect.get("city"),
            "functional_area": prospect.get("functional_area"),
            "areas_of_expertise": prospect.get("areas_of_expertise") or [],
            "context": prospect.get("context") or {},
        }

        icp_data = {
            "name": icp.get("name"),
            "description": icp.get("description"),
            "criteria": icp.get("criteria") or {},
        }

        icp_json = json.dumps(icp_data, indent=2, default=str)
        prospect_json = json.dumps(prospect_data, indent=2, default=str)
        company_json = json.dumps(company, indent=2, default=str)

        return f"""
Evaluate the following prospect against the provided Ideal Customer
Profile.

========================
IDEAL CUSTOMER PROFILE
========================

{icp_json}

========================
PROSPECT
========================

{prospect_json}

========================
PROSPECT'S COMPANY
========================

{company_json}

========================
EVALUATION
========================

Determine:

1. match_score from 0 to 100
2. confidence from 0 to 100
3. decision (qualified, disqualified or needs_review)
4. concise reasoning
5. concrete evidence

Rules:

- Do not invent information.
- Do not assume missing information.
- Missing information reduces confidence but does not disqualify.
- Evaluate against the actual ICP criteria.
- Return JSON only.
"""

    # ========================================================
    # RESULT SHAPING
    # ========================================================

    def normalize_result(
        self,
        result: dict,
        prospect: dict,
        icp: dict,
    ) -> dict[str, Any]:

        decision = result.get("decision")

        if decision not in DECISIONS:
            decision = "needs_review"

        evidence = result.get("evidence")

        if not isinstance(evidence, dict):
            evidence = {"notes": evidence} if evidence else {}

        reasoning = result.get("reasoning")

        return {
            "prospect_id": prospect["id"],
            "icp_id": icp["id"],
            "match_score": clamp_score(result.get("match_score", 0)),
            "confidence": clamp_score(result.get("confidence", 0)),
            "decision": decision,
            "reasoning": str(reasoning) if reasoning else None,
            "evidence": evidence,
            "status": "completed",
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }

    def build_failed_result(
        self,
        prospect: dict,
        icp: dict,
        error: str,
    ) -> dict[str, Any]:

        return {
            "prospect_id": prospect["id"],
            "icp_id": icp["id"],
            "match_score": 0,
            "confidence": 0,
            "decision": "needs_review",
            "reasoning": "ICP evaluation could not be completed.",
            "evidence": {"error": error},
            "status": "failed",
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }

    def save_results(self, results: list[dict]) -> None:

        if not results:
            return

        (
            supabase
            .table("prospect_icp_matches")
            .upsert(results, on_conflict="prospect_id,icp_id")
            .execute()
        )

    def build_summary(
        self,
        icp_id: str,
        campaign_id: str,
        company_ids: list[str],
        results: list[dict],
        total: int,
        failed: int,
    ) -> dict[str, Any]:

        def count(**criteria) -> int:
            return sum(
                1
                for result in results
                if all(
                    result.get(key) == value
                    for key, value in criteria.items()
                )
            )

        return {
            "icp_id": icp_id,
            "campaign_id": campaign_id,
            "company_ids": company_ids,
            "total_companies": len(company_ids),
            "total_prospects": total,
            "processed": count(status="completed"),
            "failed": failed,
            "qualified": count(status="completed", decision="qualified"),
            "disqualified": count(
                status="completed",
                decision="disqualified",
            ),
            "needs_review": count(decision="needs_review"),
        }


async def run_icp_fitment(
    icp_id: str,
    company_ids: list[str] | None = None,
    prospect_ids: list[str] | None = None,
) -> dict[str, Any]:

    return await ICPFitmentAgent().run(
        icp_id=icp_id,
        company_ids=company_ids,
        prospect_ids=prospect_ids,
    )
