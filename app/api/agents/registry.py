"""Agent registry.

Resolves an agent class together with its per-campaign configuration
from the `campaign_agents` table, so a campaign can disable an agent or
override its system prompt without a code change.
"""

from typing import Any

from agents.conversation_agent.agent import ConversationAgent
from agents.followup_agent.agent import FollowupAgent
from agents.ICP_fitment.agent import ICPFitmentAgent
from agents.personalization_agent.agent import PersonalizationAgent
from agents.research_agent.agent import ResearchAgent
from agents.strategy.agent import StrategyAgent
from core.config import AGENT_TYPES
from db.supabase_client import supabase


AGENT_CLASSES: dict[str, Any] = {
    "icp_fitment": ICPFitmentAgent,
    "research": ResearchAgent,
    "strategy": StrategyAgent,
    "personalization": PersonalizationAgent,
    "conversation": ConversationAgent,
    "followup": FollowupAgent,
}


def get_agent_config(
    campaign_id: str,
    agent_type: str,
) -> dict[str, Any]:
    """Return the campaign_agents row for this agent, or a default."""

    default = {
        "campaign_id": campaign_id,
        "agent_type": agent_type,
        "enabled": True,
        "system_prompt": None,
        "configuration": {},
    }

    try:
        response = (
            supabase
            .table("campaign_agents")
            .select("*")
            .eq("campaign_id", campaign_id)
            .eq("agent_type", agent_type)
            .maybe_single()
            .execute()
        )

        return (response.data if response else None) or default

    except Exception as exc:
        print("[REGISTRY] Failed to load agent config:", exc)

        return default


def build_agent(campaign_id: str, agent_type: str) -> Any:
    """Instantiate an agent using its campaign configuration.

    Raises ValueError when the agent type is unknown, and PermissionError
    when the campaign has switched it off.
    """

    agent_class = AGENT_CLASSES.get(agent_type)

    if not agent_class:
        raise ValueError(f"Unknown agent type: {agent_type}")

    config = get_agent_config(campaign_id, agent_type)

    if config.get("enabled") is False:
        raise PermissionError(
            f"The {agent_type} agent is disabled for this campaign."
        )

    return agent_class(system_prompt=config.get("system_prompt"))


def ensure_campaign_agents(campaign_id: str) -> list[dict[str, Any]]:
    """Create the default `campaign_agents` rows for a new campaign."""

    rows = [
        {
            "campaign_id": campaign_id,
            "agent_type": agent_type,
            "enabled": True,
            "configuration": {},
        }
        for agent_type in AGENT_TYPES
    ]

    response = (
        supabase
        .table("campaign_agents")
        .upsert(rows, on_conflict="campaign_id,agent_type")
        .execute()
    )

    return response.data or []
