import os

from google import genai
from google.genai import types


client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "gemini-embedding-001",
)


async def create_embedding(
    text: str,
    task_type: str,
) -> list[float]:

    response = await client.aio.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=768,
        ),
    )

    if not response.embeddings:
        raise RuntimeError(
            "Gemini returned no embedding"
        )

    return list(
        response.embeddings[0].values
    )


async def create_document_embedding(
    text: str,
) -> list[float]:

    return await create_embedding(
        text,
        "RETRIEVAL_DOCUMENT",
    )


async def create_query_embedding(
    text: str,
) -> list[float]:

    return await create_embedding(
        text,
        "RETRIEVAL_QUERY",
    )