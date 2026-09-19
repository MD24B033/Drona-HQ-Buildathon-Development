from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class CampaignCreate(BaseModel):
    name: str
    description: str
    icp: str

@router.post("/")
async def create_campaign(campaign: CampaignCreate):
    # TODO: Save campaign to database (PostgreSQL)
    # TODO: Connect to DronaHQ App Builder logic
    return {"message": "Campaign created in Draft state", "data": campaign.model_dump()}

@router.get("/")
async def list_campaigns():
    # TODO: Fetch from database
    return {"campaigns": []}

@router.post("/{campaign_id}/status")
async def update_campaign_status(campaign_id: str, status: str):
    """
    Status can be: Draft, Live, Paused, Completed, Archived
    """
    # TODO: Global kill switch or specific campaign pause logic
    return {"message": f"Campaign {campaign_id} status updated to {status}"}
