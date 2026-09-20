"""Request authentication.

The frontend signs in with Supabase Auth and sends the resulting access
token as `Authorization: Bearer <token>`. We verify the token against
Supabase and resolve the caller's profile row.
"""

from typing import Any

from fastapi import Depends, Header, HTTPException, status

from db.supabase_client import supabase


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    """Resolve the Supabase user behind the bearer token."""

    if not authorization:
        raise _unauthorized("Missing Authorization header.")

    scheme, _, token = authorization.partition(" ")

    if scheme.lower() != "bearer" or not token:
        raise _unauthorized("Expected a Bearer token.")

    try:
        response = supabase.auth.get_user(token)
    except Exception as exc:
        raise _unauthorized("Invalid or expired session.") from exc

    user = getattr(response, "user", None)

    if not user:
        raise _unauthorized("Invalid or expired session.")

    return {
        "id": user.id,
        "email": user.email,
    }


async def get_current_profile(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Return the caller's `profiles` row, creating it if it is missing."""

    response = (
        supabase
        .table("profiles")
        .select("*")
        .eq("id", user["id"])
        .maybe_single()
        .execute()
    )

    profile = response.data if response else None

    if profile:
        return profile

    created = (
        supabase
        .table("profiles")
        .upsert(
            {
                "id": user["id"],
                "email": user["email"],
                "onboarding_completed": False,
            },
            on_conflict="id",
        )
        .execute()
    )

    if not created.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to resolve your profile.",
        )

    return created.data[0]


def require_campaign(
    campaign_id: str,
    profile_id: str,
) -> dict[str, Any]:
    """Load a campaign, enforcing that it belongs to this profile."""

    response = (
        supabase
        .table("campaigns")
        .select("*")
        .eq("id", campaign_id)
        .eq("profile_id", profile_id)
        .maybe_single()
        .execute()
    )

    campaign = response.data if response else None

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found.",
        )

    return campaign


def require_icp(
    icp_id: str,
    profile_id: str,
) -> dict[str, Any]:
    """Load an ICP together with the campaign that owns it."""

    response = (
        supabase
        .table("icps")
        .select("*, campaigns!inner(id, profile_id)")
        .eq("id", icp_id)
        .eq("campaigns.profile_id", profile_id)
        .maybe_single()
        .execute()
    )

    icp = response.data if response else None

    if not icp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ICP not found.",
        )

    return icp
