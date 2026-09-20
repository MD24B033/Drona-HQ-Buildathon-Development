import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent_routes import router as agents_router


app = FastAPI(
    title="Sales Automation API",
    description="Backend API for the automated sales platform.",
    version="1.0.0",
)


FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://localhost:3000",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(agents_router)


@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "sales-automation-api",
        "version": "1.0.0",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
    }