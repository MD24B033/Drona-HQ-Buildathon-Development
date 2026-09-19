from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class ProspectResearchRequest(BaseModel):
    campaign_id: str
    prospect_id: str

@router.post("/research")
async def research_prospect(request: ProspectResearchRequest):
    """
    Trigger the Lead Research & Enrichment Agent
    """
    # TODO: Connect to DronaHQ Agentic AI via API, or run LangChain locally
    return {"message": "Research agent triggered"}

@router.post("/qualify")
async def qualify_prospect(request: ProspectResearchRequest):
    """
    Trigger the ICP Fitment Agent
    """
    # TODO: Evaluate prospect against campaign ICP using LLM
    return {"status": "Qualified", "reason": "Matches target role and company size"}
