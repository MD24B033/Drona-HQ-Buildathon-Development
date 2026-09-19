# Autonomous SDR - DronaHQ Buildathon

This is the backend repository for the 51-hour Inter Guild Buildathon (Building the Autonomous SDR).

## Architecture

The system is split into two halves that function as one product:
1. **Control Plane:** The frontend UI (built on **DronaHQ Apps Studio**).
2. **Intelligence Layer / Backend:** This repository, handling the API, database interactions, agent orchestration, and integrations (using **FastAPI** + **PostgreSQL**).

### Flow
1. **Human Manager** uses the DronaHQ dashboard (Control Plane) to configure campaigns, set ICPs (Ideal Customer Profiles), and assign agents.
2. The DronaHQ app sends these configurations via REST API to this **FastAPI Backend**, which saves them in a PostgreSQL database.
3. The **Intelligence Layer** (using `app/agents`) orchestrates tasks based on Campaign states (Draft -> Live -> Paused). 
4. **Agents** (ICP Fitment, Lead Research, Outreach Strategy, etc.) are executed using local LangChain/LLM wrappers OR by proxying requests to DronaHQ's Agentic AI platform.
5. All knowledge base queries (RAG) are served via `pgvector`.
6. Status updates, prospect funnels, and metrics are sent back to the DronaHQ dashboard for real-time monitoring.

## Tech Stack
* **Framework:** Python / FastAPI
* **Database:** PostgreSQL (with `pgvector` for RAG)
* **ORM:** SQLAlchemy
* **AI/Orchestration:** LangChain / DronaHQ Agentic Platform API
* **Frontend:** DronaHQ Apps Studio

## Setup Instructions
1. Initialize virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the server:
   ```bash
   uvicorn app.main:app --reload
   ```

## Folder Structure
* `/app/api`: FastAPI route handlers (the bridge between DronaHQ UI and Backend).
* `/app/models`: Database schemas (Campaigns, Prospects, Prompts).
* `/app/agents`: Logic for autonomous agents (Research, Qualification, Outreach).
* `/app/services`: Core business logic and database interactions.
