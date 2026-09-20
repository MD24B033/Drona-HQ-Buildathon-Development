"""Gemini embeddings for the campaign knowledge base."""

from google import genai
from google.genai import types

from core.config import (
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL,
    GEMINI_API_KEY,
)


client = None
if GEMINI_API_KEY and GEMINI_API_KEY != "your-gemini-api-key":
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception:
        pass



async def create_embedding(
    text: str,
    task_type: str,
) -> list[float]:

    response = await client.aio.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=EMBEDDING_DIMENSIONS,
        ),
    )

    if not response.embeddings:
        raise RuntimeError("Gemini returned no embedding")

    return list(response.embeddings[0].values)


async def create_document_embedding(text: str) -> list[float]:
    return await create_embedding(text, "RETRIEVAL_DOCUMENT")


async def create_query_embedding(text: str) -> list[float]:
    return await create_embedding(text, "RETRIEVAL_QUERY")
