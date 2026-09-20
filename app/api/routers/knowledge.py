"""Campaign knowledge base: documents, embedding and vector search."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from core.auth import get_current_profile, require_campaign
from db.supabase_client import supabase
from rag.ingest import ingest_document
from rag.retrieval import retrieve_knowledge
from schemas import (
    KnowledgeDocumentCreate,
    KnowledgeDocumentUpdate,
    KnowledgeSearch,
)


router = APIRouter(
    prefix="/campaigns/{campaign_id}/knowledge",
    tags=["knowledge"],
)


@router.get("")
async def list_documents(
    campaign_id: str,
    profile: dict[str, Any] = Depends(get_current_profile),
):
    require_campaign(campaign_id, profile["id"])

    documents = (
        supabase
        .table("knowledge_documents")
        .select(
            "id, campaign_id, title, source_type, source_url, "
            "metadata, is_active, created_at, updated_at"
        )
        .eq("campaign_id", campaign_id)
        .order("created_at", desc=True)
        .execute()
        .data
        or []
    )

    # Chunk counts tell the user whether a document is searchable yet.
    for document in documents:
        document["chunk_count"] = _chunk_count(document["id"])

    return {"documents": documents}


@router.post("", status_code=201)
async def create_document(
    campaign_id: str,
    body: KnowledgeDocumentCreate,
    profile: dict[str, Any] = Depends(get_current_profile),
):
    """Store a document and embed it into `knowledge_chunks`."""

    require_campaign(campaign_id, profile["id"])

    response = (
        supabase
        .table("knowledge_documents")
        .insert({"campaign_id": campaign_id, **body.model_dump()})
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=500,
            detail="Unable to create knowledge document.",
        )

    document = response.data[0]

    try:
        ingestion = await ingest_document(
            document_id=document["id"],
            campaign_id=campaign_id,
            content=body.content,
            metadata={"title": body.title, "source_type": body.source_type},
        )

    except Exception as exc:
        # The document is saved but unsearchable; say so rather than
        # leaving the user to guess why retrieval finds nothing.
        print("[KNOWLEDGE] Ingestion failed:", exc)

        return {
            "document": document,
            "ingestion": {"chunks": 0, "error": str(exc)},
        }

    return {"document": document, "ingestion": ingestion}


@router.get("/{document_id}")
async def get_document(
    campaign_id: str,
    document_id: str,
    profile: dict[str, Any] = Depends(get_current_profile),
):
    require_campaign(campaign_id, profile["id"])

    document = _require_document(campaign_id, document_id)

    document["chunk_count"] = _chunk_count(document_id)

    return {"document": document}


@router.patch("/{document_id}")
async def update_document(
    campaign_id: str,
    document_id: str,
    body: KnowledgeDocumentUpdate,
    profile: dict[str, Any] = Depends(get_current_profile),
):
    require_campaign(campaign_id, profile["id"])

    _require_document(campaign_id, document_id)

    payload = body.model_dump(exclude_none=True)

    if not payload:
        raise HTTPException(
            status_code=400,
            detail="No fields to update.",
        )

    response = (
        supabase
        .table("knowledge_documents")
        .update(payload)
        .eq("id", document_id)
        .execute()
    )

    document = response.data[0] if response.data else None

    ingestion = None

    # Changing the text invalidates the existing embeddings.
    if body.content is not None:
        try:
            ingestion = await ingest_document(
                document_id=document_id,
                campaign_id=campaign_id,
                content=body.content,
                metadata={"title": (document or {}).get("title")},
            )

        except Exception as exc:
            print("[KNOWLEDGE] Re-ingestion failed:", exc)

            ingestion = {"chunks": 0, "error": str(exc)}

    return {"document": document, "ingestion": ingestion}


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    campaign_id: str,
    document_id: str,
    profile: dict[str, Any] = Depends(get_current_profile),
):
    require_campaign(campaign_id, profile["id"])

    _require_document(campaign_id, document_id)

    (
        supabase
        .table("knowledge_chunks")
        .delete()
        .eq("document_id", document_id)
        .execute()
    )

    (
        supabase
        .table("knowledge_documents")
        .delete()
        .eq("id", document_id)
        .execute()
    )


@router.post("/{document_id}/reindex")
async def reindex_document(
    campaign_id: str,
    document_id: str,
    profile: dict[str, Any] = Depends(get_current_profile),
):
    """Re-chunk and re-embed a document, e.g. after a failed ingestion."""

    require_campaign(campaign_id, profile["id"])

    document = _require_document(campaign_id, document_id, with_content=True)

    ingestion = await ingest_document(
        document_id=document_id,
        campaign_id=campaign_id,
        content=document.get("content") or "",
        metadata={"title": document.get("title")},
    )

    return {"ingestion": ingestion}


@router.post("/search")
async def search_knowledge(
    campaign_id: str,
    body: KnowledgeSearch,
    profile: dict[str, Any] = Depends(get_current_profile),
):
    """Run the same vector search the agents use."""

    require_campaign(campaign_id, profile["id"])

    chunks = await retrieve_knowledge(
        campaign_id=campaign_id,
        query=body.query,
        top_k=body.top_k,
        min_similarity=body.min_similarity,
    )

    return {"chunks": chunks, "total": len(chunks)}


# ============================================================
# HELPERS
# ============================================================

def _require_document(
    campaign_id: str,
    document_id: str,
    with_content: bool = False,
) -> dict[str, Any]:

    columns = "*" if with_content else (
        "id, campaign_id, title, source_type, source_url, "
        "metadata, is_active, created_at, updated_at"
    )

    response = (
        supabase
        .table("knowledge_documents")
        .select(columns)
        .eq("id", document_id)
        .eq("campaign_id", campaign_id)
        .maybe_single()
        .execute()
    )

    document = response.data if response else None

    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    return document


def _chunk_count(document_id: str) -> int:

    try:
        response = (
            supabase
            .table("knowledge_chunks")
            .select("id", count="exact")
            .eq("document_id", document_id)
            .limit(0)
            .execute()
        )

        return response.count or 0

    except Exception:
        return 0
