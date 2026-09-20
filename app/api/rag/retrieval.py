from db.supabase_client import supabase
from api.rag.embeddings import create_query_embedding


async def retrieve_knowledge(
    campaign_id: str,
    query: str,
    top_k: int = 8,
    min_similarity: float = 0.35,
) -> list[dict]:

    embedding = await create_query_embedding(
        query
    )

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


def format_knowledge_context(
    chunks: list[dict],
) -> str:

    if not chunks:
        return "No relevant knowledge was retrieved."

    sections = []

    for index, chunk in enumerate(
        chunks,
        start=1,
    ):

        content = (
            chunk.get("content") or ""
        ).strip()

        similarity = chunk.get(
            "similarity",
            0,
        )

        if not content:
            continue

        sections.append(
            f"""
Knowledge {index}
Similarity: {float(similarity):.3f}

{content}
""".strip()
        )

    return "\n\n".join(sections)