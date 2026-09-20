"use client";

import { useCallback, useEffect, useState } from "react";
import { MessageSquare, Send } from "lucide-react";

import {
  api,
  type Conversation,
  type ConversationMessage,
} from "../../../lib/api";
import {
  Badge,
  Button,
  EmptyState,
  ErrorNote,
  Panel,
  Spinner,
  TextArea,
  formatDate,
} from "./ui";

export default function CampaignConversations({
  campaignId,
  refreshToken,
  onChanged,
}: {
  campaignId: string;
  refreshToken: number;
  onChanged: () => void;
}) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [selected, setSelected] = useState<Conversation | null>(null);

  const [loading, setLoading] = useState(true);
  const [loadingThread, setLoadingThread] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [reply, setReply] = useState("");
  const [sending, setSending] = useState(false);
  const [analysis, setAnalysis] = useState<{
    intent: string;
    sentiment: string;
    next_action: string;
    requires_human_approval: boolean;
    reasoning: string;
  } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);

    try {
      const { conversations } = await api.listConversations(campaignId);

      setConversations(conversations);

      setSelectedId((current) => current || conversations[0]?.id || null);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load conversations."
      );
    } finally {
      setLoading(false);
    }
  }, [campaignId]);

  useEffect(() => {
    load();
  }, [load, refreshToken]);

  const loadThread = useCallback(async (conversationId: string) => {
    setLoadingThread(true);

    try {
      const { conversation, messages } =
        await api.getConversation(conversationId);

      setSelected(conversation);
      setMessages(messages);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load the conversation."
      );
    } finally {
      setLoadingThread(false);
    }
  }, []);

  useEffect(() => {
    if (selectedId) loadThread(selectedId);
  }, [selectedId, loadThread]);

  /*
   * Feeds an inbound reply to the conversation agent so it can classify
   * it and decide the next step. Real replies would arrive through a
   * provider webhook.
   */
  const submitReply = async () => {
    if (!selectedId || !reply.trim()) return;

    setSending(true);
    setError(null);
    setAnalysis(null);

    try {
      const result = await api.sendReply(selectedId, reply.trim());

      setAnalysis(result.analysis);
      setReply("");

      await loadThread(selectedId);
      await load();
      onChanged();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "The conversation agent failed."
      );
    } finally {
      setSending(false);
    }
  };

  if (loading) {
    return (
      <Panel title="Conversations">
        <Spinner label="Loading conversations..." />
      </Panel>
    );
  }

  if (conversations.length === 0) {
    return (
      <Panel title="Conversations">
        <EmptyState
          icon={<MessageSquare size={24} />}
          title="No conversations yet"
          description="Send outreach to a prospect from the Prospects tab to open a thread."
        />
      </Panel>
    );
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
      {/* Thread list */}
      <Panel title="Threads">
        <div className="space-y-2">
          {conversations.map((conversation) => (
            <button
              key={conversation.id}
              type="button"
              onClick={() => setSelectedId(conversation.id)}
              className={`w-full rounded-xl border p-3 text-left transition ${
                selectedId === conversation.id
                  ? "border-indigo-500/40 bg-indigo-500/10"
                  : "border-white/10 bg-white/[0.02] hover:bg-white/5"
              }`}
            >
              <p className="truncate text-sm font-medium text-white">
                {conversation.prospects?.full_name || "Prospect"}
              </p>

              <p className="truncate text-xs text-gray-500">
                {conversation.prospects?.companies?.name ||
                  conversation.channel}
              </p>

              <div className="mt-2 flex items-center gap-2">
                <Badge value={conversation.status} />

                <span className="text-xs text-gray-600">
                  {conversation.message_count ?? 0} msgs
                </span>
              </div>
            </button>
          ))}
        </div>
      </Panel>

      {/* Thread */}
      <Panel
        title={selected?.prospects?.full_name || "Conversation"}
        description={
          selected
            ? `${selected.channel} · ${selected.status}${
                selected.next_action
                  ? ` · next: ${selected.next_action.replace(/_/g, " ")}`
                  : ""
              }`
            : undefined
        }
        action={
          selected && (
            <div className="flex items-center gap-2">
              <Badge value={selected.intent} />
              <Badge value={selected.sentiment} />
            </div>
          )
        }
      >
        <div className="space-y-4">
          <ErrorNote message={error} />

          {loadingThread ? (
            <Spinner label="Loading thread..." />
          ) : (
            <div className="max-h-[420px] space-y-3 overflow-y-auto pr-1">
              {messages.map((message) => {
                const outbound = message.direction === "outbound";

                return (
                  <div
                    key={message.id}
                    className={`flex ${
                      outbound ? "justify-end" : "justify-start"
                    }`}
                  >
                    <div
                      className={`max-w-[80%] rounded-2xl border p-4 ${
                        outbound
                          ? "border-indigo-500/20 bg-indigo-500/10"
                          : "border-white/10 bg-white/[0.03]"
                      }`}
                    >
                      <p className="mb-1.5 text-xs text-gray-500">
                        {message.sender_type} ·{" "}
                        {formatDate(message.created_at)}
                        {message.metadata?.simulated ? " · simulated" : ""}
                      </p>

                      {typeof message.metadata?.subject === "string" && (
                        <p className="mb-2 text-sm font-medium text-white">
                          {message.metadata.subject}
                        </p>
                      )}

                      <p className="whitespace-pre-wrap text-sm leading-relaxed text-gray-200">
                        {message.content}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {analysis && (
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
              <p className="mb-2 text-xs uppercase tracking-wide text-gray-500">
                Agent analysis
              </p>

              <div className="mb-2 flex flex-wrap gap-2">
                <Badge value={analysis.intent} />
                <Badge value={analysis.sentiment} />
                <Badge value={analysis.next_action} />
                {analysis.requires_human_approval && (
                  <Badge value="escalated" />
                )}
              </div>

              <p className="text-sm leading-relaxed text-gray-300">
                {analysis.reasoning}
              </p>
            </div>
          )}

          <div className="space-y-3 border-t border-white/10 pt-4">
            <p className="text-xs text-gray-500">
              Paste a reply from the prospect to let the conversation
              agent classify it and decide the next step.
            </p>

            <TextArea
              rows={3}
              value={reply}
              onChange={setReply}
              placeholder="Thanks for reaching out - could you share pricing?"
            />

            <div className="flex justify-end">
              <Button
                variant="primary"
                onClick={submitReply}
                loading={sending}
                disabled={!reply.trim()}
              >
                <Send size={15} />
                Process reply
              </Button>
            </div>
          </div>
        </div>
      </Panel>
    </div>
  );
}
