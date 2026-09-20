"use client";

import { useCallback, useEffect, useState } from "react";
import { FileText, Plus, RefreshCw, Search, Trash2 } from "lucide-react";

import { api, type KnowledgeDocument } from "../../../lib/api";
import {
  Button,
  EmptyState,
  ErrorNote,
  Field,
  Panel,
  Spinner,
  SuccessNote,
  TextArea,
  TextInput,
  formatDate,
} from "./ui";

export default function CampaignKnowledge({
  campaignId,
  onChanged,
}: {
  campaignId: string;
  onChanged: () => void;
}) {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [adding, setAdding] = useState(false);
  const [saving, setSaving] = useState(false);
  const [draft, setDraft] = useState({ title: "", content: "" });

  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [matches, setMatches] = useState<
    { content: string; similarity: number }[] | null
  >(null);

  const load = useCallback(async () => {
    setLoading(true);

    try {
      const { documents } = await api.listKnowledge(campaignId);

      setDocuments(documents);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load the knowledge base."
      );
    } finally {
      setLoading(false);
    }
  }, [campaignId]);

  useEffect(() => {
    load();
  }, [load]);

  const addDocument = async () => {
    if (!draft.title.trim() || !draft.content.trim()) {
      setError("A document needs both a title and content.");
      return;
    }

    setSaving(true);
    setError(null);
    setNotice(null);

    try {
      const { ingestion } = await api.createKnowledge(campaignId, {
        title: draft.title.trim(),
        content: draft.content.trim(),
        source_type: "text",
      });

      if (ingestion.error) {
        /*
         * The document saved but could not be embedded, so retrieval
         * will not see it until it is reindexed.
         */
        setError(
          `Saved, but embedding failed: ${ingestion.error}. Use Reindex to retry.`
        );
      } else {
        setNotice(
          `Indexed into ${ingestion.chunks} searchable ${
            ingestion.chunks === 1 ? "chunk" : "chunks"
          }.`
        );
      }

      setDraft({ title: "", content: "" });
      setAdding(false);

      await load();
      onChanged();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to save the document."
      );
    } finally {
      setSaving(false);
    }
  };

  const removeDocument = async (documentId: string) => {
    setError(null);

    try {
      await api.deleteKnowledge(campaignId, documentId);

      await load();
      onChanged();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to delete the document."
      );
    }
  };

  const reindex = async (documentId: string) => {
    setError(null);
    setNotice(null);

    try {
      const { ingestion } = await api.reindexKnowledge(
        campaignId,
        documentId
      );

      setNotice(`Reindexed into ${ingestion.chunks} chunks.`);

      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to reindex.");
    }
  };

  const runSearch = async () => {
    if (!query.trim()) return;

    setSearching(true);
    setError(null);

    try {
      const { chunks } = await api.searchKnowledge(campaignId, query);

      setMatches(chunks);
    } catch (err) {
      setError(err instanceof Error ? err.message : "The search failed.");
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="space-y-6">
      <Panel
        title="Campaign knowledge"
        description="Everything here is embedded and retrieved by the research, strategy, personalization and conversation agents."
        action={
          <Button
            variant="primary"
            size="sm"
            onClick={() => setAdding((open) => !open)}
          >
            <Plus size={15} />
            Add document
          </Button>
        }
      >
        <div className="space-y-4">
          {adding && (
            <div className="space-y-4 rounded-xl border border-white/10 bg-white/[0.03] p-4">
              <Field label="Title">
                <TextInput
                  value={draft.title}
                  onChange={(value) =>
                    setDraft((current) => ({ ...current, title: value }))
                  }
                  placeholder="Product one-pager"
                />
              </Field>

              <Field
                label="Content"
                hint="Paste product details, pricing, case studies or objection handling."
              >
                <TextArea
                  rows={8}
                  value={draft.content}
                  onChange={(value) =>
                    setDraft((current) => ({ ...current, content: value }))
                  }
                  placeholder="What the product does, who it is for, proof points..."
                />
              </Field>

              <Button
                variant="primary"
                onClick={addDocument}
                loading={saving}
              >
                Save and index
              </Button>
            </div>
          )}

          <ErrorNote message={error} />
          <SuccessNote message={notice} />

          {loading ? (
            <Spinner label="Loading knowledge base..." />
          ) : documents.length === 0 ? (
            <EmptyState
              icon={<FileText size={24} />}
              title="No knowledge documents"
              description="Without a knowledge base the agents can only use the campaign fields and prospect data."
            />
          ) : (
            <div className="space-y-2">
              {documents.map((document) => (
                <div
                  key={document.id}
                  className="flex items-center justify-between gap-4 rounded-xl border border-white/10 bg-white/[0.02] p-4"
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white/5">
                      <FileText size={16} className="text-gray-400" />
                    </div>

                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-white">
                        {document.title}
                      </p>

                      <p className="text-xs text-gray-500">
                        {document.chunk_count ?? 0} chunks ·{" "}
                        {formatDate(document.created_at)}
                        {document.chunk_count === 0 && (
                          <span className="ml-2 text-amber-400">
                            not searchable
                          </span>
                        )}
                      </p>
                    </div>
                  </div>

                  <div className="flex shrink-0 items-center gap-2">
                    <Button
                      size="sm"
                      onClick={() => reindex(document.id)}
                      title="Reindex"
                    >
                      <RefreshCw size={14} />
                    </Button>

                    <Button
                      size="sm"
                      variant="danger"
                      onClick={() => removeDocument(document.id)}
                      title="Delete"
                    >
                      <Trash2 size={14} />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </Panel>

      <Panel
        title="Test retrieval"
        description="Run the same vector search the agents use, to check what they would actually see."
      >
        <div className="space-y-4">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search
                size={16}
                className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-500"
              />

              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") runSearch();
                }}
                placeholder="How does pricing work?"
                className="h-11 w-full rounded-xl border border-white/10 bg-white/5 pl-10 pr-4 text-sm text-white outline-none transition-all placeholder:text-gray-600 focus:border-indigo-500"
              />
            </div>

            <Button variant="primary" onClick={runSearch} loading={searching}>
              Search
            </Button>
          </div>

          {matches !== null &&
            (matches.length === 0 ? (
              <p className="py-6 text-center text-sm text-gray-500">
                Nothing matched above the similarity threshold.
              </p>
            ) : (
              <div className="space-y-2">
                {matches.map((chunk, index) => (
                  <div
                    key={index}
                    className="rounded-xl border border-white/10 bg-white/[0.02] p-4"
                  >
                    <p className="mb-2 text-xs text-indigo-300">
                      similarity {chunk.similarity.toFixed(3)}
                    </p>

                    <p className="text-sm leading-relaxed text-gray-300">
                      {chunk.content.slice(0, 400)}
                      {chunk.content.length > 400 && "..."}
                    </p>
                  </div>
                ))}
              </div>
            ))}
        </div>
      </Panel>
    </div>
  );
}
