from fastapi import APIRouter
from app.api import campaigns, agents

router = APIRouter()

router.include_router(campaigns.router, prefix="/campaigns", tags=["Campaign Control Plane"])
router.include_router(agents.router, prefix="/agents", tags=["Agent Intelligence Layer"])
