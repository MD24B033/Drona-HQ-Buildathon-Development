from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.ICP_fitment.agent import ICPFitmentAgent
from db.supabase_client import supabase


router = APIRouter(
    prefix="/agents",
    tags=["agents"],
)


class ICPFitmentRequest(BaseModel):
    icp_id: str


@router.post("/icp-fitment/run")
async def run_icp_fitment(request: ICPFitmentRequest):
    agent = ICPFitmentAgent()

    try:
        result = await agent.run(
            icp_id=request.icp_id,
        )

        return {
            "success": True,
            "agent": "icp_fitment",
            "result": result,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except Exception as exc:
        print("[API] ICP fitment error:", exc)

        raise HTTPException(
            status_code=500,
            detail="ICP fitment agent failed.",
        )


@router.get("/icp-fitment/{icp_id}/results")
async def get_icp_fitment_results(icp_id: str):
    try:
        response = (
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
            .eq("icp_id", icp_id)
            .order("match_score", desc=True)
            .execute()
        )

        results = response.data or []

        qualified = sum(
            1
            for result in results
            if result.get("decision") == "qualified"
        )

        disqualified = sum(
            1
            for result in results
            if result.get("decision") == "disqualified"
        )

        needs_review = sum(
            1
            for result in results
            if result.get("decision") == "needs_review"
        )

        processing = sum(
            1
            for result in results
            if result.get("status") == "processing"
        )

        failed = sum(
            1
            for result in results
            if result.get("status") == "failed"
        )

        completed = sum(
            1
            for result in results
            if result.get("status") == "completed"
        )

        return {
            "success": True,
            "metrics": {
                "total": len(results),
                "completed": completed,
                "qualified": qualified,
                "disqualified": disqualified,
                "needs_review": needs_review,
                "processing": processing,
                "failed": failed,
            },
            "results": results,
        }

    except Exception as exc:
        print(
            "[API] Failed to load ICP results:",
            exc,
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to load ICP fitment results.",
        )