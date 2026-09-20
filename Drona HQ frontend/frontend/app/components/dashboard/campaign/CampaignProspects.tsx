"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Microscope,
  Send,
  Sparkles,
  Users,
} from "lucide-react";

import { api, type Personalization, type Prospect } from "../../../lib/api";
import {
  Badge,
  Button,
  EmptyState,
  ErrorNote,
  Panel,
  Spinner,
  formatDate,
} from "./ui";

const FILTERS = [
  { id: "", label: "All" },
  { id: "qualified", label: "Qualified" },
  { id: "needs_review", label: "Needs review" },
  { id: "disqualified", label: "Disqualified" },
];

export default function CampaignProspects({
  campaignId,
  refreshToken,
  onChanged,
}: {
  campaignId: string;
  refreshToken: number;
  onChanged: () => void;
}) {
  const [prospects, setProspects] = useState<Prospect[]>([]);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  /* Which agent is running for which prospect. */
  const [busy, setBusy] = useState<Record<string, string>>({});

  const [drafts, setDrafts] = useState<Record<string, Personalization>>({});

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const { prospects } = await api.listProspects(
        campaignId,
        filter || undefined
      );

      setProspects(prospects);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to load prospects."
      );
    } finally {
      setLoading(false);
    }
  }, [campaignId, filter]);

  useEffect(() => {
    load();
  }, [load, refreshToken]);

  const runAgent = async (
    prospectId: string,
    agent: "research" | "personalization" | "outreach" | "followup"
  ) => {
    setBusy((current) => ({ ...current, [prospectId]: agent }));
    setError(null);

    try {
      if (agent === "research") {
        await api.runResearch(campaignId, prospectId);
      } else if (agent === "personalization") {
        const { personalization } = await api.runPersonalization(
          campaignId,
          prospectId
        );

        setDrafts((current) => ({
          ...current,
          [prospectId]: personalization,
        }));
      } else if (agent === "outreach") {
        await api.sendOutreach(campaignId, prospectId);
      } else {
        await api.runFollowup(campaignId, prospectId);
      }

      await load();
      onChanged();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : `The ${agent} agent failed.`
      );
    } finally {
      setBusy((current) => {
        const next = { ...current };
        delete next[prospectId];
        return next;
      });
    }
  };

  return (
    <Panel
      title="Prospects"
      description="Everyone the agents have found at your target companies, with their pipeline state."
      action={
        <div className="flex gap-1 rounded-xl border border-white/10 bg-white/5 p-1">
          {FILTERS.map((option) => (
            <button
              key={option.id || "all"}
              type="button"
              onClick={() => setFilter(option.id)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                filter === option.id
                  ? "bg-indigo-500 text-white"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      }
    >
      <div className="space-y-4">
        <ErrorNote message={error} />

        {loading ? (
          <Spinner label="Loading prospects..." />
        ) : prospects.length === 0 ? (
          <EmptyState
            icon={<Users size={24} />}
            title="No prospects yet"
            description="Select target companies, then run discovery or ICP fitment from the Agents tab."
          />
        ) : (
          <div className="space-y-2">
            {prospects.map((prospect) => {
              const isOpen = expanded === prospect.id;
              const runningAgent = busy[prospect.id];

              return (
                <div
                  key={prospect.id}
                  className="rounded-xl border border-white/10 bg-white/[0.02]"
                >
                  <button
                    type="button"
                    onClick={() => setExpanded(isOpen ? null : prospect.id)}
                    className="flex w-full items-center justify-between gap-4 p-4 text-left"
                  >
                    <div className="flex min-w-0 items-center gap-3">
                      {isOpen ? (
                        <ChevronDown
                          size={16}
                          className="shrink-0 text-gray-500"
                        />
                      ) : (
                        <ChevronRight
                          size={16}
                          className="shrink-0 text-gray-500"
                        />
                      )}

                      <div className="min-w-0">
                        <p className="truncate font-medium text-white">
                          {prospect.full_name}
                        </p>

                        <p className="truncate text-xs text-gray-500">
                          {[prospect.current_title, prospect.companies?.name]
                            .filter(Boolean)
                            .join(" · ") || "No title"}
                        </p>
                      </div>
                    </div>

                    <div className="flex shrink-0 items-center gap-2">
                      {prospect.icp_match && (
                        <span className="text-sm font-semibold text-white">
                          {Number(prospect.icp_match.match_score).toFixed(0)}
                        </span>
                      )}

                      <Badge value={prospect.icp_match?.decision} />

                      {prospect.research && (
                        <span title="Researched">
                          <Microscope size={15} className="text-cyan-400" />
                        </span>
                      )}

                      {prospect.conversation && (
                        <Badge value={prospect.conversation.status} />
                      )}
                    </div>
                  </button>

                  {isOpen && (
                    <div className="space-y-5 border-t border-white/10 p-5">
                      {/* Actions */}
                      <div className="flex flex-wrap gap-2">
                        <Button
                          size="sm"
                          onClick={() => runAgent(prospect.id, "research")}
                          loading={runningAgent === "research"}
                        >
                          <Microscope size={14} />
                          Research
                        </Button>

                        <Button
                          size="sm"
                          onClick={() =>
                            runAgent(prospect.id, "personalization")
                          }
                          loading={runningAgent === "personalization"}
                        >
                          <Sparkles size={14} />
                          Draft message
                        </Button>

                        <Button
                          size="sm"
                          variant="primary"
                          onClick={() => runAgent(prospect.id, "outreach")}
                          loading={runningAgent === "outreach"}
                        >
                          <Send size={14} />
                          Send outreach
                        </Button>

                        <Button
                          size="sm"
                          onClick={() => runAgent(prospect.id, "followup")}
                          loading={runningAgent === "followup"}
                        >
                          Plan follow-up
                        </Button>

                        {prospect.linkedin_url && (
                          <a
                            href={prospect.linkedin_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex h-9 items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 text-sm text-gray-300 transition hover:bg-white/10"
                          >
                            <ExternalLink size={14} />
                            LinkedIn
                          </a>
                        )}
                      </div>

                      {/* ICP fitment */}
                      {prospect.icp_match?.reasoning && (
                        <Detail
                          label={`ICP fitment · ${
                            prospect.icp_match.icps?.name || "ICP"
                          } · confidence ${Number(
                            prospect.icp_match.confidence
                          ).toFixed(0)}`}
                        >
                          {prospect.icp_match.reasoning}
                        </Detail>
                      )}

                      {/* Research */}
                      {prospect.research && (
                        <div className="space-y-3">
                          <Detail
                            label={`Research · v${prospect.research.research_version} · confidence ${Number(
                              prospect.research.confidence
                            ).toFixed(0)}`}
                          >
                            {prospect.research.summary}
                          </Detail>

                          <ListDetail
                            label="Pain points"
                            values={prospect.research.pain_points}
                          />

                          <ListDetail
                            label="Buying signals"
                            values={prospect.research.buying_signals}
                          />
                        </div>
                      )}

                      {/* Strategy */}
                      {prospect.strategy && (
                        <Detail
                          label={`Strategy · ${
                            prospect.strategy.primary_channel || "—"
                          } · step ${prospect.strategy.sequence_step}`}
                        >
                          {prospect.strategy.strategy_reason}
                        </Detail>
                      )}

                      {/* Follow-up */}
                      {prospect.followup && (
                        <Detail
                          label={`Follow-up · ${prospect.followup.status} · step ${prospect.followup.current_step}/${prospect.followup.max_steps} · next ${formatDate(
                            prospect.followup.next_action_at
                          )}`}
                        >
                          {prospect.followup.reasoning ||
                            prospect.followup.stop_reason}
                        </Detail>
                      )}

                      {/* Latest draft */}
                      {drafts[prospect.id] && (
                        <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-4">
                          <p className="mb-2 text-xs uppercase tracking-wide text-indigo-300">
                            Draft message · {drafts[prospect.id].channel}
                          </p>

                          {drafts[prospect.id].subject && (
                            <p className="mb-2 text-sm font-medium text-white">
                              {drafts[prospect.id].subject}
                            </p>
                          )}

                          <p className="whitespace-pre-wrap text-sm leading-relaxed text-gray-300">
                            {drafts[prospect.id].message}
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </Panel>
  );
}

function Detail({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  if (!children) return null;

  return (
    <div>
      <p className="mb-1.5 text-xs uppercase tracking-wide text-gray-500">
        {label}
      </p>

      <p className="text-sm leading-relaxed text-gray-300">{children}</p>
    </div>
  );
}

function ListDetail({
  label,
  values,
}: {
  label: string;
  values: unknown[];
}) {
  if (!values || values.length === 0) return null;

  return (
    <div>
      <p className="mb-1.5 text-xs uppercase tracking-wide text-gray-500">
        {label}
      </p>

      <ul className="space-y-1">
        {values.slice(0, 5).map((value, index) => (
          <li
            key={index}
            className="flex gap-2 text-sm leading-relaxed text-gray-300"
          >
            <span className="text-gray-600">•</span>

            <span>
              {typeof value === "string" ? value : JSON.stringify(value)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
