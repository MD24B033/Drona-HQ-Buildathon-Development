"""Service-role Supabase client.

The backend is the only place that talks to the database. It uses the
service-role key and therefore bypasses RLS, so every router is
responsible for scoping queries to the caller's profile.
"""

from supabase import Client, create_client

from core.config import SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL


if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL is not configured")

if not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError("SUPABASE_KEY is not configured")


supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_ROLE_KEY,
)
