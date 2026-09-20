# Drona HQ — Autonomous SDR

A B2B sales automation platform: pick target companies, define an ideal
customer profile, and let a pipeline of agents find, score, research and
contact the right people.

- **Backend** — FastAPI (`app/api`), Supabase Postgres, Gemini agents
- **Frontend** — Next.js 16 App Router (`Drona HQ frontend/frontend`)

## Architecture

Supabase is used by the browser **for authentication only**. Every read
and write goes through the API, which holds the service-role key and
scopes each query to the signed-in profile. The browser sends its
Supabase access token as `Authorization: Bearer <token>`.

```
Browser ──(Supabase Auth)──► Supabase
   │
   └──(Bearer token)──► FastAPI ──► Supabase (service role)
                           │
                           └──► Gemini (agents + embeddings)
```

## The pipeline

Agents run in dependency order. Each stage writes to its own table and
every execution is recorded in `agent_runs`.

| Stage | Agent | Reads | Writes |
| --- | --- | --- | --- |
| 1 | Prospect discovery | `companies`, `icps`, `campaigns` | `prospects` |
| 2 | ICP fitment | `prospects`, `icps` | `prospect_icp_matches` |
| 3 | Research | qualified matches + knowledge base | `prospect_research` |
| 4 | Strategy | research + `outreach_events` usage | `outreach_strategies` |
| 5 | Personalization | everything above | `outreach_events` (draft) |
| 6 | Conversation | the draft | `conversations`, `conversation_messages` |
| 7 | Follow-up | the thread | `followup_plans` |

Stages 3–7 retrieve from the campaign knowledge base: documents are
chunked, embedded with `gemini-embedding-001` into `knowledge_chunks`
(`vector(768)`), and searched through the `match_knowledge_chunks` RPC.

## Running it

Both servers must be running.

### Backend

```bash
pip install -r requirements.txt
```

Copy `app/api/.env.example` to `app/api/.env` and fill in
`SUPABASE_URL`, `SUPABASE_KEY` (service role) and `GEMINI_API_KEY`.

```bash
cd "app/api" && uvicorn main:app --reload --port 8000
```

Interactive API docs: <http://localhost:8000/docs>

### Frontend

Set `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` and
`NEXT_PUBLIC_API_URL` in `Drona HQ frontend/frontend/.env.local`, then:

```bash
npm install --prefix "Drona HQ frontend/frontend"
```

```bash
npm run dev --prefix "Drona HQ frontend/frontend"
```

Open <http://localhost:3000>.

## Using it

1. Sign up, then complete company onboarding.
2. Create a campaign — it requires a first ICP.
3. **Companies** tab: pick the target companies. Nothing runs without
   at least one.
4. **Knowledge** tab: add product and pricing material so the agents
   have something factual to write from.
5. **Agents** tab: run the pipeline. `outreach` is the only stage that
   contacts anyone, and it is off by default.
6. **Prospects**, **Conversations** and **Activity** show what happened.

## Outreach delivery

`core/channels.py` is the only place that sends anything. No provider
credentials are configured, so `CHANNEL_SIMULATION=true` records sends
without delivering them — messages appear in the conversation thread
marked `simulated`.

To go live, implement the provider call in `_send_email` /
`_send_linkedin` / `_send_sms` and set the matching
`CHANNEL_<NAME>_ENABLED=true`.

Inbound replies currently arrive by pasting them into the Conversations
tab; a provider webhook would call `POST /agents/conversation/reply`
instead.

## Model configuration

`GEMINI_MODEL` sets the default for every agent, overridable per agent
(`RESEARCH_MODEL`, `STRATEGY_MODEL`, …). When the primary model is
saturated, calls retry with backoff and then fall back to
`GEMINI_FALLBACK_MODEL`.

Free-tier API keys allow only a few requests per day per model, which is
far below what a full pipeline run needs. A quota failure surfaces as
HTTP 429 with a message saying so.

## Safety rails

- Daily outreach limits are enforced by the application, not the model:
  the strategy agent is given its remaining capacity and its output is
  clamped to it.
- The conversation agent escalates to a human when a reply needs
  information it does not have — pricing, contracts, legal or security.
- Agents are told never to invent facts; missing information lowers
  confidence rather than becoming a claim.
- Any agent can be disabled per campaign from the Agents tab.
