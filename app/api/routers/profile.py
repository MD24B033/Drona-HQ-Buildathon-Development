"""Profile and onboarding endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from core.auth import get_current_profile
from db.supabase_client import supabase
from schemas import ProfileUpdate


router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("")
async def get_profile(
    profile: dict[str, Any] = Depends(get_current_profile),
):
    return {"profile": profile}


@router.patch("")
async def update_profile(
    body: ProfileUpdate,
    profile: dict[str, Any] = Depends(get_current_profile),
):
    """Save onboarding answers or later company-settings edits."""

    payload = body.model_dump(exclude_none=True)

    if not payload:
        raise HTTPException(
            status_code=400,
            detail="No fields to update.",
        )

    response = (
        supabase
        .table("profiles")
        .update(payload)
        .eq("id", profile["id"])
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=500,
            detail="Unable to update your profile.",
        )

    return {"profile": response.data[0]}
