"""Knowledge document ingestion.

A document's text is chunked, embedded with Gemini and written to
`knowledge_chunks` so the agents can retrieve it later.
"""

import asyncio
from typing import Any

from db.supabase_client import supabase
from rag.chunking import chunk_text, estimate_tokens
from rag.embeddings import create_document_embedding


EMBED_CONCURRENCY = 5


async def ingest_document(
    document_id: str,
    campaign_id: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Re-chunk and re-embed a single knowledge document."""

    chunks = chunk_text(content)

    # Replace any previous chunks for this document.
    (
        supabase
        .table("knowledge_chunks")
        .delete()
        .eq("document_id", document_id)
        .execute()
    )

    if not chunks:
        return {
            "document_id": document_id,
            "chunks": 0,
        }

    semaphore = asyncio.Semaphore(EMBED_CONCURRENCY)

    async def embed(index: int, chunk: str) -> dict[str, Any]:
        async with semaphore:
            embedding = await create_document_embedding(chunk)

        return {
            "document_id": document_id,
            "campaign_id": campaign_id,
            "chunk_index": index,
            "content": chunk,
            "token_count": estimate_tokens(chunk),
            "embedding": embedding,
            "metadata": metadata or {},
        }

    rows = await asyncio.gather(
        *[
            embed(index, chunk)
            for index, chunk in enumerate(chunks)
        ]
    )

    # Insert in batches so a large document does not blow the request size.
    batch_size = 25

    for start in range(0, len(rows), batch_size):
        (
            supabase
            .table("knowledge_chunks")
            .insert(rows[start:start + batch_size])
            .execute()
        )

    return {
        "document_id": document_id,
        "chunks": len(rows),
    }
