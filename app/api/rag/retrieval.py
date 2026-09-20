"""Vector search over `knowledge_chunks`."""

from core.config import RAG_MIN_SIMILARITY, RAG_TOP_K
from db.supabase_client import supabase
from rag.embeddings import create_query_embedding


async def retrieve_knowledge(
    campaign_id: str,
    query: str,
    top_k: int = RAG_TOP_K,
    min_similarity: float = RAG_MIN_SIMILARITY,
) -> list[dict]:
    """Return the campaign knowledge chunks closest to `query`.

    Retrieval is best-effort: a campaign with no knowledge base, or a
    transient embedding failure, must not take an agent down.
    """

    if not query or not query.strip():
        return []

    try:
        embedding = await create_query_embedding(query)

        response = (
            supabase
            .rpc(
                "match_knowledge_chunks",
                {
                    "query_embedding": embedding,
                    "match_campaign_id": campaign_id,
                    "match_count": top_k,
                    "min_similarity": min_similarity,
                },
            )
            .execute()
        )

        return response.data or []

    except Exception as exc:
        print("[RAG] Retrieval failed:", exc)

        return []


def format_knowledge_context(chunks: list[dict]) -> str:

    if not chunks:
        return "No relevant knowledge was retrieved."

    sections = []

    for index, chunk in enumerate(chunks, start=1):

        content = (chunk.get("content") or "").strip()

        if not content:
            continue

        similarity = chunk.get("similarity", 0)

        sections.append(
            f"Knowledge {index}\n"
            f"Similarity: {float(similarity):.3f}\n\n"
            f"{content}"
        )

    return "\n\n".join(sections)
