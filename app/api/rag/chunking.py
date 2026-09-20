"""Text normalisation and chunking for the knowledge base."""

import re

from core.config import CHUNK_OVERLAP, CHUNK_SIZE


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def estimate_tokens(text: str) -> int:
    """Rough token estimate; good enough for `knowledge_chunks.token_count`."""

    return max(1, len(text) // 4)


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """Split text into overlapping word windows."""

    text = normalize_text(text)

    if not text:
        return []

    words = text.split()

    if len(words) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0

    while start < len(words):

        end = min(start + chunk_size, len(words))

        chunk = " ".join(words[start:end]).strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(words):
            break

        start = max(end - overlap, start + 1)

    return chunks
