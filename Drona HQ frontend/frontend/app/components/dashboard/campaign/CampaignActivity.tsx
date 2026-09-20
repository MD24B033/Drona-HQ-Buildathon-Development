"use client";

import { useCallback, useEffect, useState } from "react";
import { Activity, RefreshCw } from "lucide-react";

import {
  api,
  type AgentRun,
  type FollowupPlan,
  type OutreachEvent,
  type Strategy,
} from "../../../lib/api";
import {
  Badge,
  Button,
  EmptyState,
  ErrorNote,
  Panel,
  Spinner,
  agentLabel,
  formatDate,
} from "./ui";

export default function CampaignActivity({
  campaignId,
  refreshToken,
}: {
  campaignId: string;
  refreshToken: number;
}) {
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [events, setEvents] = useState<OutreachEvent[]>([]);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [followups, setFollowups] = useState<FollowupPlan[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [runsResult, eventsResult, strategyResult, followupResult] =
        await Promise.all([
          api.listRuns(campaignId),
          api.listEvents(campaignId),
          api.listStrategies(campaignId),
          api.listFollowups(campaignId),
        ]);

      setRuns(runsResult.runs);
      setEvents(eventsResult.events);
      setStrategies(strategyResult.strategies);
      setFollowups(followupResult.followups);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to load activity."
      );
    } finally {
      setLoading(false);
    }
  }, [campaignId]);

  useEffect(() => {
    load();
  }, [load, refreshToken]);

  if (loading) {
    return (
      <Panel title="Activity">
        <Spinner label="Loading activity..." />
      </Panel>
    );
  }

  return (
    <div className="space-y-6">
      <ErrorNote message={error} />

      <Panel
        title="Agent runs"
        description="Every agent execution, with its latency, model and any error."
        action={
          <Button size="sm" onClick={load}>
            <RefreshCw size={14} />
            Refresh
          </Button>
        }
      >
        {runs.length === 0 ? (
          <EmptyState
            icon={<Activity size={24} />}
            title="Nothing has run yet"
            description="Run the pipeline from the Agents tab to see execution history here."
          />
        ) : (
          <div className="space-y-2">
            {runs.map((run) => (
              <div
                key={run.id}
                className="rounded-xl border border-white/10 bg-white/[0.02] p-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <Badge value={run.status} />

                    <span className="text-sm font-medium text-white">
                      {agentLabel(run.agent_type)}
                    </span>
                  </div>

                  <div className="flex items-center gap-4 text-xs text-gray-500">
                    {run.model && <span>{run.model}</span>}

                    {run.latency_ms !== null && (
                      <span>{(run.latency_ms / 1000).toFixed(1)}s</span>
                    )}

                    <span>{formatDate(run.started_at)}</span>
                  </div>
                </div>

                {run.error && (
                  <p className="mt-2 line-clamp-2 text-xs text-red-300">
                    {run.error}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </Panel>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel
          title="Outreach plan"
          description="Who the strategy agent cleared for contact."
        >
          {strategies.length === 0 ? (
            <p className="py-8 text-center text-sm text-gray-500">
              No outreach has been planned yet.
            </p>
          ) : (
            <div className="space-y-2">
              {strategies.map((strategy) => (
                <div
                  key={strategy.id}
                  className="rounded-xl border border-white/10 bg-white/[0.02] p-4"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-medium text-white">
                      {strategy.prospects?.full_name || "Prospect"}
                    </p>

                    <Badge value={strategy.primary_channel || "email"} />
                  </div>

                  <p className="mt-1 text-xs text-gray-500">
                    Step {strategy.sequence_step} · {strategy.delay_hours}h
                    delay
                  </p>

                  {strategy.strategy_reason && (
                    <p className="mt-2 text-sm text-gray-400">
                      {strategy.strategy_reason}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </Panel>

        <Panel
          title="Follow-up queue"
          description="Planned next touches, soonest first."
        >
          {followups.length === 0 ? (
            <p className="py-8 text-center text-sm text-gray-500">
              No follow-ups planned yet.
            </p>
          ) : (
            <div className="space-y-2">
              {followups.map((plan) => (
                <div
                  key={plan.id}
                  className="rounded-xl border border-white/10 bg-white/[0.02] p-4"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-medium text-white">
                      {plan.prospects?.full_name || "Prospect"}
                    </p>

                    <Badge value={plan.status} />
                  </div>

                  <p className="mt-1 text-xs text-gray-500">
                    Step {plan.current_step}/{plan.max_steps}
                    {plan.next_channel && ` · ${plan.next_channel}`} ·{" "}
                    {formatDate(plan.next_action_at)}
                  </p>

                  {(plan.reasoning || plan.stop_reason) && (
                    <p className="mt-2 text-sm text-gray-400">
                      {plan.stop_reason || plan.reasoning}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>

      <Panel
        title="Event feed"
        description="Drafts, sends and replies recorded against this campaign."
      >
        {events.length === 0 ? (
          <p className="py-8 text-center text-sm text-gray-500">
            No events yet.
          </p>
        ) : (
          <div className="space-y-2">
            {events.map((event) => (
              <div
                key={event.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/10 bg-white/[0.02] px-4 py-3"
              >
                <div className="flex items-center gap-3">
                  <Badge value={event.status} />

                  <span className="text-sm text-gray-200">
                    {event.event_type.replace(/_/g, " ")}
                  </span>

                  {event.channel && (
                    <span className="text-xs text-gray-500">
                      {event.channel}
                    </span>
                  )}
                </div>

                <span className="text-xs text-gray-500">
                  {formatDate(event.created_at)}
                </span>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
