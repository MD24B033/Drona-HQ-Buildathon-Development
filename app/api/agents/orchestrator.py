"""Campaign pipeline orchestrator.

Runs the agents in dependency order for one campaign:

    discovery -> ICP fitment -> research -> strategy
              -> personalization + conversation -> follow-up

Each stage is optional, each is recorded in `agent_runs`, and a failure
in one prospect never stops the rest of the campaign.
"""

import asyncio
from typing import Any

from agents.prospect_discovery.agent import run_prospect_discovery_batch
from agents.registry import build_agent
from core.runs import record_event, track_run
from db.supabase_client import supabase


STAGES = [
    "discovery",
    "icp_fitment",
    "research",
    "strategy",
    "outreach",
    "followup",
]

PROSPECT_CONCURRENCY = 4


class PipelineOrchestrator:

    def __init__(self, campaign_id: str):
        self.campaign_id = campaign_id

    async def run(
        self,
        stages: list[str] | None = None,
        icp_id: str | None = None,
        send_outreach: bool = False,
    ) -> dict[str, Any]:
        """Execute the requested stages in order."""

        selected = [
            stage
            for stage in STAGES
            if stage in (stages or STAGES)
        ]

        results: dict[str, Any] = {}

        record_event(
            campaign_id=self.campaign_id,
            event_type="pipeline_started",
            status="running",
            payload={"stages": selected, "icp_id": icp_id},
        )

        for stage in selected:
            try:
                results[stage] = await self._run_stage(
                    stage=stage,
                    icp_id=icp_id,
                    send_outreach=send_outreach,
                )

            except Exception as exc:
                print(f"[PIPELINE] Stage {stage} failed:", exc)

                results[stage] = {
                    "success": False,
                    "error": str(exc),
                }

        record_event(
            campaign_id=self.campaign_id,
            event_type="pipeline_completed",
            status="completed",
            payload={
                "stages": selected,
                "failed_stages": [
                    stage
                    for stage, result in results.items()
                    if not result.get("success", True)
                ],
            },
        )

        return {
            "success": True,
            "campaign_id": self.campaign_id,
            "stages": selected,
            "results": results,
        }

    async def _run_stage(
        self,
        stage: str,
        icp_id: str | None,
        send_outreach: bool,
    ) -> dict[str, Any]:

        runner = {
            "discovery": self._run_discovery,
            "icp_fitment": self._run_icp_fitment,
            "research": self._run_research,
            "strategy": self._run_strategy,
            "outreach": self._run_outreach,
            "followup": self._run_followup,
        }[stage]

        if stage == "outreach" and not send_outreach:
            return {
                "success": True,
                "skipped": True,
                "reason": (
                    "Outreach was not requested. Pass send_outreach=true "
                    "to contact prospects."
                ),
            }

        return await runner(icp_id)

    # ========================================================
    # STAGES
    # ========================================================

    async def _run_discovery(self, icp_id: str | None) -> dict[str, Any]:

        icp_ids = self._icp_ids(icp_id)

        company_ids = self._campaign_company_ids()

        if not icp_ids or not company_ids:
            return {
                "success": True,
                "skipped": True,
                "reason": (
                    "Discovery needs at least one ICP and one target "
                    "company."
                ),
            }

        discovered: list[dict[str, Any]] = []

        for current_icp_id in icp_ids:
            async with track_run(
                agent_type="prospect_discovery",
                campaign_id=self.campaign_id,
                payload={
                    "icp_id": current_icp_id,
                    "company_ids": company_ids,
                },
            ) as run:
                results = await run_prospect_discovery_batch(
                    company_ids=company_ids,
                    icp_id=current_icp_id,
                    run_fitment=False,
                )

                run["output"] = {
                    "companies": len(results),
                    "saved": sum(
                        result.get("saved_count", 0)
                        for result in results
                    ),
                }

                discovered.extend(results)

        return {
            "success": True,
            "companies_processed": len(discovered),
            "prospects_saved": sum(
                result.get("saved_count", 0)
                for result in discovered
            ),
        }

    async def _run_icp_fitment(
        self,
        icp_id: str | None,
    ) -> dict[str, Any]:

        icp_ids = self._icp_ids(icp_id)

        if not icp_ids:
            return {
                "success": True,
                "skipped": True,
                "reason": "This campaign has no ICPs.",
            }

        agent = build_agent(self.campaign_id, "icp_fitment")

        summaries = []

        for current_icp_id in icp_ids:
            async with track_run(
                agent_type="icp_fitment",
                campaign_id=self.campaign_id,
                payload={"icp_id": current_icp_id},
                model=agent.model,
            ) as run:
                summary = await agent.run(icp_id=current_icp_id)

                run["output"] = summary

                summaries.append(summary)

        return {
            "success": True,
            "icps": len(summaries),
            "summaries": summaries,
        }

    async def _run_research(self, icp_id: str | None) -> dict[str, Any]:

        prospect_ids = self._qualified_prospect_ids()

        if not prospect_ids:
            return {
                "success": True,
                "skipped": True,
                "reason": "No qualified prospects to research.",
            }

        agent = build_agent(self.campaign_id, "research")

        return await self._for_each_prospect(
            prospect_ids=prospect_ids,
            agent_type="research",
            model=agent.model,
            action=lambda prospect_id: agent.run(
                prospect_id=prospect_id,
                campaign_id=self.campaign_id,
            ),
        )

    async def _run_strategy(self, icp_id: str | None) -> dict[str, Any]:

        agent = build_agent(self.campaign_id, "strategy")

        async with track_run(
            agent_type="strategy",
            campaign_id=self.campaign_id,
            payload={"campaign_id": self.campaign_id},
            model=agent.model,
        ) as run:
            result = await agent.run(campaign_id=self.campaign_id)

            run["output"] = result.get("strategy")

            return result

    async def _run_outreach(self, icp_id: str | None) -> dict[str, Any]:

        prospect_ids = self._strategy_prospect_ids()

        if not prospect_ids:
            return {
                "success": True,
                "skipped": True,
                "reason": (
                    "No prospects are cleared for contact. Run the "
                    "strategy stage first."
                ),
            }

        agent = build_agent(self.campaign_id, "conversation")

        return await self._for_each_prospect(
            prospect_ids=prospect_ids,
            agent_type="conversation",
            model=agent.model,
            action=lambda prospect_id: agent.start_outreach(
                prospect_id=prospect_id,
                campaign_id=self.campaign_id,
                icp_id=icp_id,
            ),
        )

    async def _run_followup(self, icp_id: str | None) -> dict[str, Any]:

        prospect_ids = self._contacted_prospect_ids()

        if not prospect_ids:
            return {
                "success": True,
                "skipped": True,
                "reason": "No prospects have been contacted yet.",
            }

        agent = build_agent(self.campaign_id, "followup")

        return await self._for_each_prospect(
            prospect_ids=prospect_ids,
            agent_type="followup",
            model=agent.model,
            action=lambda prospect_id: agent.run(
                prospect_id=prospect_id,
                campaign_id=self.campaign_id,
            ),
        )

    # ========================================================
    # HELPERS
    # ========================================================

    async def _for_each_prospect(
        self,
        prospect_ids: list[str],
        agent_type: str,
        model: str,
        action,
    ) -> dict[str, Any]:
        """Run one agent across many prospects, bounded and fault-tolerant."""

        semaphore = asyncio.Semaphore(PROSPECT_CONCURRENCY)

        async def run_one(prospect_id: str) -> dict[str, Any]:
            async with semaphore:
                try:
                    async with track_run(
                        agent_type=agent_type,
                        campaign_id=self.campaign_id,
                        prospect_id=prospect_id,
                        payload={"prospect_id": prospect_id},
                        model=model,
                    ) as run:
                        result = await action(prospect_id)

                        run["output"] = result

                        return {
                            "prospect_id": prospect_id,
                            "success": True,
                        }

                except Exception as exc:
                    print(
                        f"[PIPELINE] {agent_type} failed for "
                        f"{prospect_id}:",
                        exc,
                    )

                    return {
                        "prospect_id": prospect_id,
                        "success": False,
                        "error": str(exc),
                    }

        results = await asyncio.gather(
            *[run_one(prospect_id) for prospect_id in prospect_ids]
        )

        succeeded = [result for result in results if result["success"]]

        return {
            "success": True,
            "total": len(results),
            "succeeded": len(succeeded),
            "failed": len(results) - len(succeeded),
            "results": results,
        }

    def _icp_ids(self, icp_id: str | None) -> list[str]:

        if icp_id:
            return [icp_id]

        response = (
            supabase
            .table("icps")
            .select("id")
            .eq("campaign_id", self.campaign_id)
            .execute()
        )

        return [row["id"] for row in (response.data or [])]

    def _campaign_company_ids(self) -> list[str]:

        response = (
            supabase
            .table("campaign_companies")
            .select("company_id")
            .eq("campaign_id", self.campaign_id)
            .execute()
        )

        return [
            row["company_id"]
            for row in (response.data or [])
            if row.get("company_id")
        ]

    def _qualified_prospect_ids(self) -> list[str]:

        response = (
            supabase
            .table("prospect_icp_matches")
            .select("prospect_id, icps!inner(campaign_id)")
            .eq("icps.campaign_id", self.campaign_id)
            .eq("decision", "qualified")
            .eq("status", "completed")
            .execute()
        )

        return list(
            {
                row["prospect_id"]
                for row in (response.data or [])
                if row.get("prospect_id")
            }
        )

    def _strategy_prospect_ids(self) -> list[str]:

        response = (
            supabase
            .table("outreach_strategies")
            .select("prospect_id")
            .eq("campaign_id", self.campaign_id)
            .eq("should_contact", True)
            .execute()
        )

        return [
            row["prospect_id"]
            for row in (response.data or [])
            if row.get("prospect_id")
        ]

    def _contacted_prospect_ids(self) -> list[str]:

        response = (
            supabase
            .table("conversations")
            .select("prospect_id")
            .eq("campaign_id", self.campaign_id)
            .execute()
        )

        return list(
            {
                row["prospect_id"]
                for row in (response.data or [])
                if row.get("prospect_id")
            }
        )


async def run_pipeline(
    campaign_id: str,
    stages: list[str] | None = None,
    icp_id: str | None = None,
    send_outreach: bool = False,
) -> dict[str, Any]:

    return await PipelineOrchestrator(campaign_id).run(
        stages=stages,
        icp_id=icp_id,
        send_outreach=send_outreach,
    )
