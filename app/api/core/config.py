"""Central configuration for the backend.

Every value can be overridden through the environment (app/api/.env).
"""

import os

from dotenv import load_dotenv


load_dotenv()


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


# ============================================================
# SERVICE
# ============================================================

PROJECT_NAME = "Drona HQ Sales Automation API"

VERSION = "1.0.0"

FRONTEND_URLS = [
    url.strip()
    for url in os.getenv(
        "FRONTEND_URL",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if url.strip()
]


# ============================================================
# SUPABASE
# ============================================================

SUPABASE_URL = os.getenv("SUPABASE_URL")

SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_KEY")


# ============================================================
# GEMINI
# ============================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash").strip()

# Used when the primary model stays saturated after every retry.
FALLBACK_MODEL = os.getenv(
    "GEMINI_FALLBACK_MODEL",
    "gemini-3.5-flash-lite",
).strip()

EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "gemini-embedding-001",
).strip()

# knowledge_chunks.embedding is vector(768), so this must stay 768.
EMBEDDING_DIMENSIONS = 768


def model_for(agent_type: str) -> str:
    """Per-agent model override, e.g. RESEARCH_MODEL=gemini-3.6-flash."""

    return os.getenv(
        f"{agent_type.upper()}_MODEL",
        DEFAULT_MODEL,
    ).strip()


# ============================================================
# AGENT TYPES
# ============================================================

AGENT_TYPES = [
    "prospect_discovery",
    "icp_fitment",
    "research",
    "strategy",
    "personalization",
    "conversation",
    "followup",
]


# ============================================================
# RAG
# ============================================================

RAG_TOP_K = _int("RAG_TOP_K", 8)

RAG_MIN_SIMILARITY = _float("RAG_MIN_SIMILARITY", 0.35)

CHUNK_SIZE = _int("CHUNK_SIZE", 1200)

CHUNK_OVERLAP = _int("CHUNK_OVERLAP", 200)


# ============================================================
# ICP FITMENT
# ============================================================

ICP_FITMENT_CONCURRENCY = _int("ICP_FITMENT_CONCURRENCY", 10)

ICP_FITMENT_BATCH_SIZE = _int("ICP_FITMENT_BATCH_SIZE", 100)

ICP_FITMENT_MAX_RETRIES = _int("ICP_FITMENT_MAX_RETRIES", 3)

ICP_FITMENT_RETRY_DELAY = _float("ICP_FITMENT_RETRY_DELAY", 1.0)


# ============================================================
# STRATEGY
# ============================================================

DEFAULT_DAILY_TARGET = _int("DEFAULT_DAILY_TARGET", 20)

MAX_DAILY_TARGET = _int("MAX_DAILY_TARGET", 50)

STRATEGY_MIN_MATCH_SCORE = _int("STRATEGY_MIN_MATCH_SCORE", 70)

STRATEGY_MIN_CONFIDENCE = _int("STRATEGY_MIN_CONFIDENCE", 50)


# ============================================================
# DISCOVERY
# ============================================================

DISCOVERY_MAX_CANDIDATES = _int("DISCOVERY_MAX_CANDIDATES", 20)
