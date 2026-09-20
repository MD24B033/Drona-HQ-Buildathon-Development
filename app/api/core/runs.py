"""Agent run + outreach event telemetry.

Every agent execution is recorded in `agent_runs` so the dashboard can
show what ran, how long it took and what came back.
"""

import json
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from db.supabase_client import supabase


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _jsonable(value: Any) -> Any:
    """Coerce arbitrary payloads into something jsonb will accept."""

    return json.loads(
        json.dumps(
            value if value is not None else {},
            default=str,
        )
    )


def start_run(
    agent_type: str,
    campaign_id: str | None,
    prospect_id: str | None,
    payload: dict[str, Any],
    model: str | None = None,
) -> str | None:
    """Insert a `running` agent_runs row and return its id."""

    try:
        response = (
            supabase
            .table("agent_runs")
            .insert(
                {
                    "campaign_id": campaign_id,
                    "prospect_id": prospect_id,
                    "agent_type": agent_type,
                    "status": "running",
                    "input": _jsonable(payload),
                    "output": {},
                    "started_at": _now(),
                    "model": model,
                    "prompt_version": "v1",
                }
            )
            .execute()
        )

        if response.data:
            return response.data[0]["id"]

    except Exception as exc:
        print("[RUNS] Failed to open agent run:", exc)

    return None


def finish_run(
    run_id: str | None,
    status: str,
    output: Any = None,
    error: str | None = None,
    latency_ms: int | None = None,
) -> None:
    """Close out an agent_runs row."""

    if not run_id:
        return

    try:
        (
            supabase
            .table("agent_runs")
            .update(
                {
                    "status": status,
                    "output": _jsonable(output),
                    "error": error,
                    "completed_at": _now(),
                    "latency_ms": latency_ms,
                }
            )
            .eq("id", run_id)
            .execute()
        )

    except Exception as exc:
        print("[RUNS] Failed to close agent run:", exc)


@asynccontextmanager
async def track_run(
    agent_type: str,
    campaign_id: str | None = None,
    prospect_id: str | None = None,
    payload: dict[str, Any] | None = None,
    model: str | None = None,
):
    """Wrap an agent execution so success and failure are both recorded.

    Usage:

        async with track_run("research", campaign_id) as run:
            result = await agent.run(...)
            run["output"] = result
    """

    started = time.perf_counter()

    run_id = start_run(
        agent_type=agent_type,
        campaign_id=campaign_id,
        prospect_id=prospect_id,
        payload=payload or {},
        model=model,
    )

    handle: dict[str, Any] = {
        "id": run_id,
        "output": None,
    }

    try:
        yield handle

    except Exception as exc:
        finish_run(
            run_id=run_id,
            status="failed",
            output=handle.get("output"),
            error=str(exc),
            latency_ms=int(
                (time.perf_counter() - started) * 1000
            ),
        )

        raise

    finish_run(
        run_id=run_id,
        status="completed",
        output=handle.get("output"),
        latency_ms=int(
            (time.perf_counter() - started) * 1000
        ),
    )


def record_event(
    campaign_id: str,
    event_type: str,
    status: str,
    payload: dict[str, Any] | None = None,
    prospect_id: str | None = None,
    agent_type: str | None = None,
    channel: str | None = None,
) -> dict[str, Any] | None:
    """Append a row to `outreach_events`."""

    try:
        response = (
            supabase
            .table("outreach_events")
            .insert(
                {
                    "campaign_id": campaign_id,
                    "prospect_id": prospect_id,
                    "agent_type": agent_type,
                    "event_type": event_type,
                    "channel": channel,
                    "status": status,
                    "payload": _jsonable(payload or {}),
                }
            )
            .execute()
        )

        return response.data[0] if response.data else None

    except Exception as exc:
        print("[RUNS] Failed to record outreach event:", exc)

        return None
