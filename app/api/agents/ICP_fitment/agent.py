import asyncio
import json
import os
from typing import Any

from google import genai
from google.genai import types

from db.supabase_client import supabase


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are an ICP Fitment Agent for a B2B sales automation system.

Your job is to determine how well a prospect matches an Ideal Customer Profile (ICP).

You are evaluating an individual prospect against the provided ICP.

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

Field rules:

match_score:
A number from 0 to 100 representing how strongly
the prospect matches the ICP.

confidence:
A number from 0 to 100 representing how confident
you are in the assessment based on the available evidence.

decision:
Must be exactly one of:

qualified
disqualified
needs_review

reasoning:
A concise explanation of why the prospect received
the score and decision.

evidence:
An object containing concrete evidence from the supplied
prospect and ICP data.

Scoring principles:

90-100:
Very strong ICP match.

The most important ICP criteria are clearly satisfied
with strong evidence.

70-89:
Strong ICP match.

Most important criteria appear satisfied, but there
may be minor uncertainty or missing information.

50-69:
Potential or partial match.

There is some supporting evidence, but meaningful
information is missing, ambiguous, or conflicting.

0-49:
Poor match.

There is strong evidence that the prospect does not
match important ICP criteria.

Decision rules:

qualified:
Use when there is strong evidence that the prospect
matches the important ICP criteria.

disqualified:
Use when there is strong evidence that the prospect
does not match important ICP criteria.

needs_review:
Use when important information is missing, ambiguous,
contradictory, or insufficient to confidently qualify
or disqualify the prospect.

Important rules:

- Never invent company size.
- Never invent industry.
- Never invent revenue.
- Never invent technology usage.
- Never invent geography.
- Never invent responsibilities.
- Never invent seniority.
- Never invent company characteristics.
- Never invent prospect characteristics.
- Never infer a fact that is not reasonably supported by
  the supplied data.
- Missing information is NOT automatically negative evidence.
- Missing information should generally reduce confidence.
- Evaluate the actual ICP criteria rather than generic
  assumptions about the prospect.
- Evidence must come from the supplied data.
- Keep reasoning concise and factual.
- Return JSON only.
"""


# ============================================================
# CONFIGURATION
# ============================================================

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not configured"
    )


MODEL = os.getenv(
    "ICP_FITMENT_MODEL",
    "gemini-3.6-flash",
).strip()


MAX_CONCURRENCY = int(
    os.getenv(
        "ICP_FITMENT_CONCURRENCY",
        "10",
    )
)


BATCH_SIZE = int(
    os.getenv(
        "ICP_FITMENT_BATCH_SIZE",
        "100",
    )
)


MAX_RETRIES = int(
    os.getenv(
        "ICP_FITMENT_MAX_RETRIES",
        "3",
    )
)


RETRY_BASE_DELAY = float(
    os.getenv(
        "ICP_FITMENT_RETRY_DELAY",
        "1",
    )
)


# ============================================================
# GEMINI CLIENT
# ============================================================

gemini = genai.Client(
    api_key=GEMINI_API_KEY,
)

print(
    f"[ICP FITMENT] Gemini model: {MODEL}"
)


# ============================================================
# ICP FITMENT AGENT
# ============================================================

class ICPFitmentAgent:

    def __init__(self):
        self.semaphore = asyncio.Semaphore(
            MAX_CONCURRENCY
        )

    # ========================================================
    # MAIN PIPELINE
    # ========================================================

    async def run(
        self,
        icp_id: str,
    ) -> dict[str, Any]:

        """
        Run ICP fitment for every prospect belonging
        to the companies selected for the ICP's campaign.

        Flow:

            ICP
             ↓
            Campaign
             ↓
            Campaign Companies
             ↓
            Company IDs
             ↓
            Prospects
             ↓
            Gemini evaluation
             ↓
            Batch upsert
             ↓
            Metrics
        """

        # ----------------------------------------------------
        # 1. Get ICP
        # ----------------------------------------------------

        icp = await asyncio.to_thread(
            self.get_icp,
            icp_id,
        )

        if not icp:
            raise ValueError(
                f"ICP {icp_id} not found."
            )

        campaign_id = icp.get(
            "campaign_id"
        )

        if not campaign_id:
            raise ValueError(
                f"ICP {icp_id} is not associated with a campaign."
            )

        # ----------------------------------------------------
        # 2. Get companies selected for campaign
        # ----------------------------------------------------

        company_ids = await asyncio.to_thread(
            self.get_campaign_company_ids,
            campaign_id,
        )

        if not company_ids:
            return {
                "icp_id": icp_id,
                "campaign_id": campaign_id,
                "company_ids": [],
                "total_companies": 0,
                "total_prospects": 0,
                "processed": 0,
                "failed": 0,
                "qualified": 0,
                "disqualified": 0,
                "needs_review": 0,
            }

        # ----------------------------------------------------
        # 3. Get prospects belonging to selected companies
        # ----------------------------------------------------

        prospects = await asyncio.to_thread(
            self.get_prospects,
            company_ids,
        )

        total_prospects = len(
            prospects
        )

        if total_prospects == 0:
            return {
                "icp_id": icp_id,
                "campaign_id": campaign_id,
                "company_ids": company_ids,
                "total_companies": len(
                    company_ids
                ),
                "total_prospects": 0,
                "processed": 0,
                "failed": 0,
                "qualified": 0,
                "disqualified": 0,
                "needs_review": 0,
            }

        # ----------------------------------------------------
        # 4. Process prospects in batches
        # ----------------------------------------------------

        all_results: list[
            dict[str, Any]
        ] = []

        processed = 0
        failed = 0

        for batch_start in range(
            0,
            total_prospects,
            BATCH_SIZE,
        ):

            batch = prospects[
                batch_start:
                batch_start + BATCH_SIZE
            ]

            batch_end = min(
                batch_start + BATCH_SIZE,
                total_prospects,
            )

            print(
                "[ICP FITMENT] "
                f"Processing prospects "
                f"{batch_start + 1}-{batch_end} "
                f"of {total_prospects}"
            )

            # ------------------------------------------------
            # Run Gemini evaluations concurrently
            # ------------------------------------------------

            tasks = [
                self.evaluate_prospect(
                    prospect=prospect,
                    icp=icp,
                )
                for prospect in batch
            ]

            batch_results = await asyncio.gather(
                *tasks,
                return_exceptions=True,
            )

            valid_results: list[
                dict[str, Any]
            ] = []

            for result in batch_results:

                if isinstance(
                    result,
                    Exception,
                ):
                    failed += 1

                    print(
                        "[ICP FITMENT] "
                        "Unexpected evaluation error:",
                        result,
                    )

                    continue

                if result is None:
                    failed += 1
                    continue

                valid_results.append(
                    result
                )

                if result["status"] == "failed":
                    failed += 1
                else:
                    processed += 1

            # ------------------------------------------------
            # Save batch immediately
            # ------------------------------------------------

            if valid_results:

                await asyncio.to_thread(
                    self.save_results,
                    valid_results,
                )

                all_results.extend(
                    valid_results
                )

            print(
                "[ICP FITMENT] "
                f"Batch complete | "
                f"processed={processed} | "
                f"failed={failed}"
            )

        # ----------------------------------------------------
        # 5. Final summary
        # ----------------------------------------------------

        return self.build_summary(
            icp_id=icp_id,
            campaign_id=campaign_id,
            company_ids=company_ids,
            results=all_results,
            total=total_prospects,
            failed=failed,
        )

    # ========================================================
    # GET ICP
    # ========================================================

    def get_icp(
        self,
        icp_id: str,
    ) -> dict | None:

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
            .eq(
                "id",
                icp_id,
            )
            .single()
            .execute()
        )

        return response.data

    # ========================================================
    # GET CAMPAIGN COMPANIES
    # ========================================================

    def get_campaign_company_ids(
        self,
        campaign_id: str,
    ) -> list[str]:

        response = (
            supabase
            .table("campaign_companies")
            .select(
                "company_id"
            )
            .eq(
                "campaign_id",
                campaign_id,
            )
            .execute()
        )

        rows = response.data or []

        return [
            row["company_id"]
            for row in rows
            if row.get("company_id")
        ]

    # ========================================================
    # GET PROSPECTS
    # ========================================================

    def get_prospects(
        self,
        company_ids: list[str],
    ) -> list[dict]:

        if not company_ids:
            return []

        response = (
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
            .in_(
                "company_id",
                company_ids,
            )
            .execute()
        )

        return response.data or []

    # ========================================================
    # EVALUATE ONE PROSPECT
    # ========================================================

    async def evaluate_prospect(
        self,
        prospect: dict,
        icp: dict,
    ) -> dict[str, Any]:

        async with self.semaphore:

            prompt = self.build_prompt(
                prospect=prospect,
                icp=icp,
            )

            for attempt in range(
                MAX_RETRIES + 1
            ):

                try:

                    response = await asyncio.to_thread(
                        gemini.models.generate_content,
                        model=MODEL,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            response_mime_type="application/json",
                        ),
                    )

                    if not response.text:
                        raise ValueError(
                            "Gemini returned an empty response."
                        )

                    result = json.loads(
                        response.text
                    )

                    return self.normalize_result(
                        result=result,
                        prospect=prospect,
                        icp=icp,
                    )

                except Exception as exc:

                    error_text = str(exc)

                    # ----------------------------------------
                    # Permanent errors should NOT be retried
                    # ----------------------------------------

                    permanent_error = (
                        "404" in error_text
                        or "NOT_FOUND" in error_text
                        or "invalid model" in error_text.lower()
                        or "model is not found" in error_text.lower()
                        or "permission denied" in error_text.lower()
                        or "api key" in error_text.lower()
                    )

                    is_last_attempt = (
                        attempt >= MAX_RETRIES
                    )

                    if permanent_error or is_last_attempt:

                        print(
                            "[ICP FITMENT] "
                            f"Failed prospect "
                            f"{prospect.get('id')}: "
                            f"{error_text}"
                        )

                        return self.build_failed_result(
                            prospect=prospect,
                            icp=icp,
                            error=error_text,
                        )

                    delay = (
                        RETRY_BASE_DELAY
                        * (
                            2 ** attempt
                        )
                    )

                    print(
                        "[ICP FITMENT] "
                        f"Request failed for "
                        f"{prospect.get('id')}. "
                        f"Retry {attempt + 1}/"
                        f"{MAX_RETRIES} "
                        f"in {delay:.1f}s"
                    )

                    await asyncio.sleep(
                        delay
                    )

        return self.build_failed_result(
            prospect=prospect,
            icp=icp,
            error="Unknown evaluation error.",
        )

    # ========================================================
    # BUILD PROMPT
    # ========================================================

    def build_prompt(
        self,
        prospect: dict,
        icp: dict,
    ) -> str:

        prospect_data = {
            "full_name": prospect.get(
                "full_name"
            ),
            "current_title": prospect.get(
                "current_title"
            ),
            "linkedin_url": prospect.get(
                "linkedin_url"
            ),
            "country": prospect.get(
                "country"
            ),
            "city": prospect.get(
                "city"
            ),
            "functional_area": prospect.get(
                "functional_area"
            ),
            "areas_of_expertise": (
                prospect.get(
                    "areas_of_expertise"
                )
                or []
            ),
            "context": (
                prospect.get(
                    "context"
                )
                or {}
            ),
        }

        icp_data = {
            "name": icp.get(
                "name"
            ),
            "description": icp.get(
                "description"
            ),
            "criteria": (
                icp.get(
                    "criteria"
                )
                or {}
            ),
        }

        return f"""
Evaluate the following prospect against
the provided Ideal Customer Profile.

========================
IDEAL CUSTOMER PROFILE
========================

{json.dumps(
    icp_data,
    indent=2,
    default=str,
)}

========================
PROSPECT
========================

{json.dumps(
    prospect_data,
    indent=2,
    default=str,
)}

========================
EVALUATION
========================

Determine:

1. match_score from 0 to 100
2. confidence from 0 to 100
3. decision
4. concise reasoning
5. concrete evidence

Decision must be exactly one of:

qualified
disqualified
needs_review

Rules:

- Do not invent information.
- Do not assume missing information.
- Missing information should reduce confidence.
- Missing information should NOT automatically result
  in disqualification.
- Evaluate against the actual ICP criteria.
- Use only evidence contained in the supplied data.
- Return JSON only.
"""

    # ========================================================
    # NORMALIZE GEMINI RESULT
    # ========================================================

    def normalize_result(
        self,
        result: dict,
        prospect: dict,
        icp: dict,
    ) -> dict[str, Any]:

        match_score = self.clamp(
            result.get(
                "match_score",
                0,
            )
        )

        confidence = self.clamp(
            result.get(
                "confidence",
                0,
            )
        )

        decision = self.normalize_decision(
            result.get(
                "decision"
            )
        )

        reasoning = result.get(
            "reasoning"
        )

        evidence = result.get(
            "evidence"
        )

        if not isinstance(
            evidence,
            dict,
        ):
            evidence = {}

        return {
            "prospect_id": prospect["id"],
            "icp_id": icp["id"],
            "match_score": match_score,
            "confidence": confidence,
            "decision": decision,
            "reasoning": (
                str(reasoning)
                if reasoning
                else None
            ),
            "evidence": evidence,
            "status": "completed",
        }

    # ========================================================
    # FAILED RESULT
    # ========================================================

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
            "reasoning": (
                "ICP evaluation could not be completed."
            ),
            "evidence": {
                "error": error,
            },
            "status": "failed",
        }

    # ========================================================
    # SAVE RESULTS
    # ========================================================

    def save_results(
        self,
        results: list[dict],
    ):

        if not results:
            return

        (
            supabase
            .table(
                "prospect_icp_matches"
            )
            .upsert(
                results,
                on_conflict=(
                    "prospect_id,icp_id"
                ),
            )
            .execute()
        )

    # ========================================================
    # BUILD METRICS
    # ========================================================

    def build_summary(
        self,
        icp_id: str,
        campaign_id: str,
        company_ids: list[str],
        results: list[dict],
        total: int,
        failed: int,
    ) -> dict[str, Any]:

        qualified = sum(
            1
            for result in results
            if (
                result["status"]
                == "completed"
                and result["decision"]
                == "qualified"
            )
        )

        disqualified = sum(
            1
            for result in results
            if (
                result["status"]
                == "completed"
                and result["decision"]
                == "disqualified"
            )
        )

        needs_review = sum(
            1
            for result in results
            if result["decision"]
            == "needs_review"
        )

        completed = sum(
            1
            for result in results
            if result["status"]
            == "completed"
        )

        return {
            "icp_id": icp_id,
            "campaign_id": campaign_id,
            "company_ids": company_ids,
            "total_companies": len(
                company_ids
            ),
            "total_prospects": total,
            "processed": completed,
            "failed": failed,
            "qualified": qualified,
            "disqualified": disqualified,
            "needs_review": needs_review,
        }

    # ========================================================
    # HELPERS
    # ========================================================

    @staticmethod
    def clamp(
        value: Any,
    ) -> float:

        try:
            value = float(value)

        except (
            ValueError,
            TypeError,
        ):
            return 0

        return round(
            max(
                0,
                min(
                    100,
                    value,
                ),
            ),
            2,
        )

    @staticmethod
    def normalize_decision(
        decision: Any,
    ) -> str:

        allowed = {
            "qualified",
            "disqualified",
            "needs_review",
        }

        if decision in allowed:
            return decision

        return "needs_review"