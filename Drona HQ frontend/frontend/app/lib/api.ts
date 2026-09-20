"use client";

/**
 * Typed client for the FastAPI backend.
 *
 * The backend owns every database read and write; the browser only
 * carries the Supabase access token so the API can identify the caller.
 */

import { supabase } from "./supabase/client";

/*
 * NEXT_PUBLIC_* values are inlined at build time, so this must be set
 * in the Vercel project before the build runs. Falling back to
 * localhost in production would leave the deployed app calling the
 * visitor's own machine, so fail loudly instead.
 */
const configuredApiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(
  /\/+$/,
  ""
);

if (!configuredApiUrl && process.env.NODE_ENV === "production") {
  throw new Error(
    "NEXT_PUBLIC_API_URL is not set. Point it at the deployed API " +
      "(for example https://your-api.up.railway.app) and rebuild."
  );
}

const API_URL = configuredApiUrl || "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function authHeader(): Promise<Record<string, string>> {
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session?.access_token) {
    throw new ApiError("You are not signed in.", 401);
  }

  return { Authorization: `Bearer ${session.access_token}` };
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    ...(await authHeader()),
    ...((options.headers as Record<string, string>) || {}),
  };

  if (options.body) {
    headers["Content-Type"] = "application/json";
  }

  let response: Response;

  try {
    response = await fetch(`${API_URL}${path}`, { ...options, headers });
  } catch {
    throw new ApiError(
      `Cannot reach the API at ${API_URL}. Is the backend running?`,
      0
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();

  let body: unknown = null;

  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
  }

  if (!response.ok) {
    const detail =
      (body as { detail?: unknown })?.detail ?? body ?? response.statusText;

    throw new ApiError(
      typeof detail === "string" ? detail : JSON.stringify(detail),
      response.status
    );
  }

  return body as T;
}

function query(params: Record<string, string | number | undefined>) {
  const search = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  });

  const serialized = search.toString();

  return serialized ? `?${serialized}` : "";
}

/* ============================================================
   TYPES
   ============================================================ */

export interface Profile {
  id: string;
  email: string | null;
  full_name: string | null;
  company_name: string | null;
  company_website: string | null;
  employee_count: number | null;
  industry: string | null;
  business_model: string | null;
  company_description: string | null;
  onboarding_completed: boolean;
}

export interface Campaign {
  id: string;
  profile_id: string;
  created_at: string;
  updated_at: string;
  geography: string[];
  target_personas: string[];
  objective: string;
  prompts: Record<string, unknown>;
  agent_instructions: string;
  campaign_specific_knowledge: string | null;
  outreach_strategy: string;
  qualification_criteria: string[];
  channel_configuration: Record<string, unknown>;
  daily_limits: number;
  human_approval_rules: Record<string, unknown>;
  icp_count?: number;
  company_count?: number;
}

export interface ICP {
  id: string;
  campaign_id: string;
  name: string;
  description: string | null;
  criteria: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Company {
  id: string;
  name: string;
  website: string | null;
  linkedin_url: string | null;
  industry: string | null;
  employee_count: number | null;
  country: string | null;
  city: string | null;
  description: string | null;
}

export interface ICPMatch {
  id: string;
  prospect_id: string;
  icp_id: string;
  match_score: number;
  confidence: number;
  decision: "qualified" | "disqualified" | "needs_review";
  reasoning: string | null;
  evidence: Record<string, unknown> | null;
  status: string;
  evaluated_at: string | null;
  icps?: { id: string; name: string };
  prospects?: {
    id: string;
    full_name: string;
    current_title: string | null;
    linkedin_url: string | null;
    companies?: { id: string; name: string } | null;
  } | null;
}

export interface Research {
  id: string;
  summary: string | null;
  company_summary: string | null;
  role_summary: string | null;
  pain_points: unknown[];
  buying_signals: unknown[];
  relevant_events: unknown[];
  technologies: unknown[];
  evidence: unknown[];
  confidence: number;
  research_version: number;
  updated_at: string;
}

export interface Strategy {
  id: string;
  prospect_id: string;
  should_contact: boolean;
  primary_channel: string | null;
  secondary_channel: string | null;
  objective: string | null;
  sequence_step: number;
  delay_hours: number;
  strategy_reason: string | null;
  constraints: Record<string, unknown>;
  prospects?: { id: string; full_name: string; current_title: string | null };
}

export interface FollowupPlan {
  id: string;
  prospect_id: string;
  current_step: number;
  max_steps: number;
  next_action_at: string | null;
  next_channel: string | null;
  status: string;
  stop_reason: string | null;
  reasoning: string | null;
  prospects?: { id: string; full_name: string; current_title: string | null };
}

export interface Prospect {
  id: string;
  company_id: string | null;
  full_name: string;
  current_title: string | null;
  linkedin_url: string | null;
  country: string | null;
  city: string | null;
  functional_area: string | null;
  areas_of_expertise: string[] | null;
  context: Record<string, unknown> | null;
  created_at: string;
  companies?: { id: string; name: string; industry: string | null } | null;
  icp_match?: ICPMatch | null;
  research?: Research | null;
  strategy?: Strategy | null;
  followup?: FollowupPlan | null;
  conversation?: Conversation | null;
}

export interface Conversation {
  id: string;
  prospect_id: string;
  campaign_id: string;
  channel: string;
  status: string;
  intent: string | null;
  sentiment: string | null;
  next_action: string | null;
  assigned_agent: string | null;
  created_at: string;
  updated_at: string;
  message_count?: number;
  prospects?: {
    id: string;
    full_name: string;
    current_title: string | null;
    companies?: { id: string; name: string } | null;
  } | null;
}

export interface ConversationMessage {
  id: string;
  conversation_id: string;
  direction: "inbound" | "outbound";
  sender_type: "agent" | "prospect" | "human";
  content: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface CampaignAgent {
  id: string;
  campaign_id: string;
  agent_type: string;
  enabled: boolean;
  system_prompt: string | null;
  configuration: Record<string, unknown>;
}

export interface KnowledgeDocument {
  id: string;
  campaign_id: string;
  title: string;
  source_type: string;
  source_url: string | null;
  content?: string;
  is_active: boolean;
  created_at: string;
  chunk_count?: number;
}

export interface OutreachEvent {
  id: string;
  campaign_id: string;
  prospect_id: string | null;
  agent_type: string | null;
  event_type: string;
  channel: string | null;
  status: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface AgentRun {
  id: string;
  campaign_id: string;
  prospect_id: string | null;
  agent_type: string;
  status: string;
  error: string | null;
  started_at: string;
  completed_at: string | null;
  latency_ms: number | null;
  model: string | null;
}

export interface CampaignStats {
  icps: number;
  companies: number;
  evaluated_prospects: number;
  qualified_prospects: number;
  researched_prospects: number;
  planned_outreach: number;
  conversations: number;
  knowledge_documents: number;
}

export interface CampaignDetail {
  campaign: Campaign;
  icps: ICP[];
  companies: Company[];
  company_ids: string[];
  agents: CampaignAgent[];
  stats: CampaignStats;
}

export interface ICPFitmentMetrics {
  total: number;
  completed: number;
  qualified: number;
  disqualified: number;
  needs_review: number;
  processing: number;
  failed: number;
}

export interface Personalization {
  channel: string;
  subject: string;
  message: string;
  personalization_angle: string;
  personalization_points: string[];
  call_to_action: string;
  evidence: unknown[];
  confidence: number;
}

/* ============================================================
   API
   ============================================================ */

export const api = {
  /* -------- profile -------- */

  getProfile: () => request<{ profile: Profile }>("/profile"),

  updateProfile: (body: Partial<Profile>) =>
    request<{ profile: Profile }>("/profile", {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  /* -------- campaigns -------- */

  listCampaigns: () =>
    request<{ campaigns: Campaign[] }>("/campaigns"),

  createCampaign: (body: Record<string, unknown>) =>
    request<{ campaign: Campaign; icp: ICP }>("/campaigns", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  getCampaign: (id: string) =>
    request<CampaignDetail>(`/campaigns/${id}`),

  updateCampaign: (id: string, body: Record<string, unknown>) =>
    request<{ campaign: Campaign }>(`/campaigns/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  deleteCampaign: (id: string) =>
    request<void>(`/campaigns/${id}`, { method: "DELETE" }),

  /* -------- icps -------- */

  listICPs: (campaignId: string) =>
    request<{ icps: ICP[] }>(`/campaigns/${campaignId}/icps`),

  createICP: (campaignId: string, body: Record<string, unknown>) =>
    request<{ icp: ICP }>(`/campaigns/${campaignId}/icps`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  getICP: (campaignId: string, icpId: string) =>
    request<{ icp: ICP }>(`/campaigns/${campaignId}/icps/${icpId}`),

  updateICP: (
    campaignId: string,
    icpId: string,
    body: Record<string, unknown>
  ) =>
    request<{ icp: ICP }>(`/campaigns/${campaignId}/icps/${icpId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  deleteICP: (campaignId: string, icpId: string) =>
    request<void>(`/campaigns/${campaignId}/icps/${icpId}`, {
      method: "DELETE",
    }),

  /* -------- companies -------- */

  listCompanies: (search?: string) =>
    request<{ companies: Company[] }>(`/companies${query({ search })}`),

  createCompany: (body: Record<string, unknown>) =>
    request<{ company: Company }>("/companies", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  setCampaignCompanies: (campaignId: string, companyIds: string[]) =>
    request<{ company_ids: string[] }>(
      `/campaigns/${campaignId}/companies`,
      {
        method: "PUT",
        body: JSON.stringify({ company_ids: companyIds }),
      }
    ),

  /* -------- prospects -------- */

  listProspects: (campaignId: string, decision?: string) =>
    request<{ prospects: Prospect[]; total: number }>(
      `/prospects${query({ campaign_id: campaignId, decision })}`
    ),

  getProspect: (prospectId: string, campaignId: string) =>
    request<{
      prospect: Prospect;
      icp_matches: ICPMatch[];
      research: Research | null;
      strategy: Strategy | null;
      followup: FollowupPlan | null;
      conversations: (Conversation & {
        conversation_messages: ConversationMessage[];
      })[];
    }>(`/prospects/${prospectId}${query({ campaign_id: campaignId })}`),

  /* -------- knowledge -------- */

  listKnowledge: (campaignId: string) =>
    request<{ documents: KnowledgeDocument[] }>(
      `/campaigns/${campaignId}/knowledge`
    ),

  createKnowledge: (campaignId: string, body: Record<string, unknown>) =>
    request<{
      document: KnowledgeDocument;
      ingestion: { chunks: number; error?: string };
    }>(`/campaigns/${campaignId}/knowledge`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  deleteKnowledge: (campaignId: string, documentId: string) =>
    request<void>(`/campaigns/${campaignId}/knowledge/${documentId}`, {
      method: "DELETE",
    }),

  reindexKnowledge: (campaignId: string, documentId: string) =>
    request<{ ingestion: { chunks: number } }>(
      `/campaigns/${campaignId}/knowledge/${documentId}/reindex`,
      { method: "POST" }
    ),

  searchKnowledge: (campaignId: string, q: string) =>
    request<{ chunks: { content: string; similarity: number }[] }>(
      `/campaigns/${campaignId}/knowledge/search`,
      { method: "POST", body: JSON.stringify({ query: q }) }
    ),

  /* -------- agent configuration -------- */

  listCampaignAgents: (campaignId: string) =>
    request<{ agents: CampaignAgent[] }>(
      `/campaigns/${campaignId}/agents`
    ),

  updateCampaignAgent: (
    campaignId: string,
    agentType: string,
    body: Record<string, unknown>
  ) =>
    request<{ agent: CampaignAgent }>(
      `/campaigns/${campaignId}/agents/${agentType}`,
      { method: "PATCH", body: JSON.stringify(body) }
    ),

  /* -------- agents -------- */

  runDiscovery: (icpId: string, companyIds?: string[]) =>
    request<{ summary: Record<string, number> }>("/agents/discovery/run", {
      method: "POST",
      body: JSON.stringify({ icp_id: icpId, company_ids: companyIds }),
    }),

  runICPFitment: (icpId: string, companyIds?: string[]) =>
    request<{ result: Record<string, unknown> }>(
      "/agents/icp-fitment/run",
      {
        method: "POST",
        body: JSON.stringify({ icp_id: icpId, company_ids: companyIds }),
      }
    ),

  getICPFitmentResults: (icpId: string) =>
    request<{ metrics: ICPFitmentMetrics; results: ICPMatch[] }>(
      `/agents/icp-fitment/${icpId}/results`
    ),

  runResearch: (campaignId: string, prospectId: string) =>
    request<{ research: Research }>("/agents/research/run", {
      method: "POST",
      body: JSON.stringify({
        campaign_id: campaignId,
        prospect_id: prospectId,
      }),
    }),

  runStrategy: (campaignId: string) =>
    request<{
      strategy: {
        campaign_status: string;
        reason: string;
        daily_target: number;
        remaining_capacity: number;
        eligible_prospects: number;
        selected_prospects: number;
      };
    }>("/agents/strategy/run", {
      method: "POST",
      body: JSON.stringify({ campaign_id: campaignId }),
    }),

  runPersonalization: (campaignId: string, prospectId: string) =>
    request<{ personalization: Personalization }>(
      "/agents/personalization/run",
      {
        method: "POST",
        body: JSON.stringify({
          campaign_id: campaignId,
          prospect_id: prospectId,
        }),
      }
    ),

  sendOutreach: (
    campaignId: string,
    prospectId: string,
    channel?: string
  ) =>
    request<{
      conversation_id: string;
      channel: string;
      simulated: boolean;
      personalization: Personalization;
    }>("/agents/conversation/outreach", {
      method: "POST",
      body: JSON.stringify({
        campaign_id: campaignId,
        prospect_id: prospectId,
        channel,
      }),
    }),

  sendReply: (conversationId: string, content: string) =>
    request<{
      analysis: {
        intent: string;
        sentiment: string;
        next_action: string;
        requires_human_approval: boolean;
        reasoning: string;
      };
      reply_sent: boolean;
    }>("/agents/conversation/reply", {
      method: "POST",
      body: JSON.stringify({
        conversation_id: conversationId,
        content,
      }),
    }),

  runFollowup: (campaignId: string, prospectId: string) =>
    request<{ followup: FollowupPlan }>("/agents/followup/run", {
      method: "POST",
      body: JSON.stringify({
        campaign_id: campaignId,
        prospect_id: prospectId,
      }),
    }),

  runPipeline: (
    campaignId: string,
    stages?: string[],
    sendOutreach = false
  ) =>
    request<{
      stages: string[];
      results: Record<string, Record<string, unknown>>;
    }>("/agents/pipeline/run", {
      method: "POST",
      body: JSON.stringify({
        campaign_id: campaignId,
        stages,
        send_outreach: sendOutreach,
      }),
    }),

  /* -------- activity -------- */

  listConversations: (campaignId: string) =>
    request<{ conversations: Conversation[] }>(
      `/conversations${query({ campaign_id: campaignId })}`
    ),

  getConversation: (conversationId: string) =>
    request<{
      conversation: Conversation;
      messages: ConversationMessage[];
    }>(`/conversations/${conversationId}`),

  listEvents: (campaignId: string) =>
    request<{ events: OutreachEvent[] }>(
      `/events${query({ campaign_id: campaignId })}`
    ),

  listStrategies: (campaignId: string) =>
    request<{ strategies: Strategy[] }>(
      `/strategies${query({ campaign_id: campaignId })}`
    ),

  listFollowups: (campaignId: string) =>
    request<{ followups: FollowupPlan[] }>(
      `/followups${query({ campaign_id: campaignId })}`
    ),

  listRuns: (campaignId: string) =>
    request<{ runs: AgentRun[] }>(
      `/agents/runs${query({ campaign_id: campaignId })}`
    ),
};
