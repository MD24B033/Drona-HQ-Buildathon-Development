"""Request bodies for the API.

Responses are returned as plain dicts straight from Supabase so the
frontend always sees the real column names.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


# ============================================================
# PROFILE
# ============================================================

class ProfileUpdate(BaseModel):
    company_name: str | None = None
    company_website: str | None = None
    employee_count: int | None = None
    industry: str | None = None
    business_model: str | None = None
    company_description: str | None = None
    full_name: str | None = None
    onboarding_completed: bool | None = None


# ============================================================
# CAMPAIGNS
# ============================================================

class CampaignCreate(BaseModel):
    objective: str = Field(min_length=1)
    geography: list[str] = Field(default_factory=list)
    target_personas: list[str] = Field(default_factory=list)
    agent_instructions: str = ""
    campaign_specific_knowledge: str | None = None
    outreach_strategy: str = ""
    qualification_criteria: list[str] = Field(default_factory=list)
    prompts: dict[str, Any] = Field(default_factory=dict)
    channel_configuration: dict[str, Any] = Field(default_factory=dict)
    daily_limits: int = 50
    human_approval_rules: dict[str, Any] = Field(default_factory=dict)


class CampaignUpdate(BaseModel):
    objective: str | None = None
    geography: list[str] | None = None
    target_personas: list[str] | None = None
    agent_instructions: str | None = None
    campaign_specific_knowledge: str | None = None
    outreach_strategy: str | None = None
    qualification_criteria: list[str] | None = None
    prompts: dict[str, Any] | None = None
    channel_configuration: dict[str, Any] | None = None
    daily_limits: int | None = None
    human_approval_rules: dict[str, Any] | None = None


class CampaignWithICPCreate(CampaignCreate):
    """Create a campaign and its mandatory first ICP in one call."""

    icp: "ICPCreate"


# ============================================================
# ICPS
# ============================================================

class ICPCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    criteria: dict[str, Any] = Field(default_factory=dict)


class ICPUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    criteria: dict[str, Any] | None = None


# ============================================================
# COMPANIES
# ============================================================

class CompanyCreate(BaseModel):
    name: str = Field(min_length=1)
    website: str | None = None
    linkedin_url: str | None = None
    industry: str | None = None
    employee_count: int | None = None
    country: str | None = None
    city: str | None = None
    description: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class CampaignCompaniesUpdate(BaseModel):
    company_ids: list[str] = Field(default_factory=list)


# ============================================================
# CAMPAIGN AGENTS
# ============================================================

class CampaignAgentUpdate(BaseModel):
    enabled: bool | None = None
    system_prompt: str | None = None
    configuration: dict[str, Any] | None = None


# ============================================================
# KNOWLEDGE
# ============================================================

class KnowledgeDocumentCreate(BaseModel):
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    source_type: str = "text"
    source_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class KnowledgeDocumentUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    source_type: str | None = None
    source_url: str | None = None
    metadata: dict[str, Any] | None = None
    is_active: bool | None = None


class KnowledgeSearch(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = 8
    min_similarity: float = 0.35


# ============================================================
# AGENT RUNS
# ============================================================

class ICPFitmentRequest(BaseModel):
    icp_id: str
    company_ids: list[str] | None = None
    prospect_ids: list[str] | None = None


class DiscoveryRequest(BaseModel):
    icp_id: str
    company_ids: list[str] | None = None
    run_fitment: bool = True


class ResearchRequest(BaseModel):
    campaign_id: str
    prospect_id: str


class StrategyRequest(BaseModel):
    campaign_id: str


class PersonalizationRequest(BaseModel):
    prospect_id: str
    campaign_id: str | None = None
    icp_id: str | None = None


class OutreachRequest(BaseModel):
    campaign_id: str
    prospect_id: str
    icp_id: str | None = None
    channel: Literal["email", "linkedin", "sms", "voice"] | None = None


class ReplyRequest(BaseModel):
    conversation_id: str
    content: str = Field(min_length=1)
    channel_message_id: str | None = None


class FollowupRequest(BaseModel):
    campaign_id: str
    prospect_id: str
    conversation_id: str | None = None


class PipelineRequest(BaseModel):
    campaign_id: str
    stages: list[str] | None = None
    icp_id: str | None = None
    send_outreach: bool = False


CampaignWithICPCreate.model_rebuild()
