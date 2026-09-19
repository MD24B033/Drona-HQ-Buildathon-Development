from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import router as api_router

app = FastAPI(
    title="Autonomous SDR Backend",
    description="Backend for Control Plane and Intelligence Layer (DronaHQ Buildathon)",
    version="1.0.0",
)

# CORS configuration to allow requests from DronaHQ frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "SDR Backend is running! Control Plane API ready."}
