"""Drona HQ sales automation API.

Run from this directory:

    uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import FRONTEND_URLS, PROJECT_NAME, VERSION
from routers import agents, campaigns, companies, conversations, knowledge
from routers import profile as profile_router


app = FastAPI(
    title=PROJECT_NAME,
    description=(
        "Backend for the autonomous SDR platform: campaigns, ICPs, "
        "prospects, the campaign knowledge base and the agent pipeline."
    ),
    version=VERSION,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_URLS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(profile_router.router)
app.include_router(campaigns.router)
app.include_router(knowledge.router)
app.include_router(companies.router)
app.include_router(conversations.router)
app.include_router(agents.router)


@app.get("/", tags=["health"])
async def root():
    return {
        "status": "ok",
        "service": "drona-hq-sales-automation-api",
        "version": VERSION,
        "docs": "/docs",
    }


@app.get("/health", tags=["health"])
async def health():
    """Liveness plus a cheap database round trip."""

    from db.supabase_client import supabase

    try:
        supabase.table("campaigns").select("id").limit(1).execute()

        database = "connected"

    except Exception as exc:
        print("[HEALTH] Database check failed:", exc)

        database = "unavailable"

    return {
        "status": "healthy" if database == "connected" else "degraded",
        "database": database,
    }
