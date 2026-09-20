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

## Deploying

Frontend on Vercel, backend on Railway, both from this one repository.

### 1. Push

```bash
git add -A && git commit -m "Wire up frontend and backend" && git push
```

### 2. Backend on Railway

1. **New Project → Deploy from GitHub repo**, pick this repo.
2. Leave **Root Directory** empty. `railway.json` at the repo root does
   the rest: Nixpacks installs from `requirements.txt`, then starts
   `uvicorn` from `app/api` bound to `0.0.0.0:$PORT`. Python is pinned
   by `.python-version`.
3. Add **Variables**:

   | Variable | Value |
   | --- | --- |
   | `SUPABASE_URL` | your Supabase project URL |
   | `SUPABASE_KEY` | the **service role** key, not the anon key |
   | `GEMINI_API_KEY` | your Gemini key |
   | `GEMINI_MODEL` | `gemini-3.5-flash` |
   | `GEMINI_FALLBACK_MODEL` | `gemini-3.5-flash-lite` |
   | `FRONTEND_URL` | your Vercel production URL (added in step 4) |
   | `CHANNEL_SIMULATION` | `true` until you wire up a real provider |

4. **Settings → Networking → Generate Domain**. Copy the
   `https://….up.railway.app` URL.
5. Check `https://<your-api>/health` returns
   `{"status":"healthy","database":"connected"}`. Railway uses this
   same path as its healthcheck.

### 3. Frontend on Vercel

1. **Add New → Project**, import the same repo.
2. Set **Root Directory** to `Drona HQ frontend/frontend`. This is the
   one setting that matters — Vercel autodetects Next.js from there.
3. Add **Environment Variables** (all three, for every environment):

   | Variable | Value |
   | --- | --- |
   | `NEXT_PUBLIC_SUPABASE_URL` | your Supabase project URL |
   | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | the **anon** key |
   | `NEXT_PUBLIC_API_URL` | the Railway URL, no trailing slash |

   These are inlined at build time, so a missing one **fails the build**
   with a message naming the variable rather than deploying something
   broken.
4. Deploy, then copy the production URL.

### 4. Connect the two

1. Back in Railway, set `FRONTEND_URL` to the Vercel production URL
   (e.g. `https://drona-hq.vercel.app`) and redeploy.
2. To let Vercel **preview** deployments reach the API too, also set
   `FRONTEND_URL_REGEX` to a pattern matching them, e.g.
   `https://drona-hq-.*\.vercel\.app`. Keep it specific — credentials
   are allowed on these requests, so a broad `.*` would open the API to
   any origin.
3. In **Supabase → Authentication → URL Configuration**:
   - **Site URL** → your Vercel production URL (used by confirmation
     emails).
   - **Redirect URLs** → add `https://<your-app>.vercel.app/auth/callback`,
     plus `http://localhost:3000/auth/callback` for local work, and a
     preview wildcard if you use Google sign-in on previews.

### Deployment notes

- **Long agent runs.** Agent endpoints are synchronous and a single
  agent takes roughly 15–70s; `POST /agents/pipeline/run` across many
  prospects can run for minutes and may hit the platform's request
  timeout. Run individual stages from the Agents tab rather than the
  whole pipeline, or move the orchestrator onto a background worker
  before running it at scale.
- **Free-tier Gemini quota** is per day per model and is the first
  thing you will hit — see *Model configuration* below.
- **Cold starts.** The first request after an idle period pays the
  container start plus a Supabase round trip.
- **Secrets.** `app/api/.env` and `.env.local` are gitignored; the
  committed `.env.example` files hold placeholders only. The service
  role key belongs only in Railway, never in a `NEXT_PUBLIC_*` variable.

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
