"use client";

import { useState } from "react";
import { Bot, Workflow } from "lucide-react";

import {
  api,
  type CampaignAgent,
  type ICP,
  type ICPFitmentMetrics,
  type ICPMatch,
} from "../../../lib/api";
import ICPFitmentAgent from "./ICPFitmentAgent";
import {
  Badge,
  Button,
  EmptyState,
  ErrorNote,
  Panel,
  SuccessNote,
  agentLabel,
} from "./ui";

export interface ICPFitmentState {
  running: boolean;
  metrics: ICPFitmentMetrics | null;
  results: ICPMatch[];
  error: string | null;
}

/*
 * The pipeline stages, in the order the backend runs them.
 * `outreach` is deliberately left out of the default selection: it is
 * the only stage that contacts anybody.
 */
const STAGES = [
  {
    id: "discovery",
    label: "Discovery",
    description: "Find people at the target companies.",
  },
  {
    id: "icp_fitment",
    label: "ICP fitment",
    description: "Score every prospect against each ICP.",
  },
  {
    id: "research",
    label: "Research",
    description: "Build sales intelligence on qualified prospects.",
  },
  {
    id: "strategy",
    label: "Strategy",
    description: "Decide who to contact today, and how.",
  },
  {
    id: "outreach",
    label: "Outreach",
    description: "Write and send the first message.",
  },
  {
    id: "followup",
    label: "Follow-up",
    description: "Plan the next touch for contacted prospects.",
  },
];

export default function CampaignAgents({
  campaignId,
  icps,
  agents,
  fitmentStates,
  onRunFitment,
  onRefreshFitment,
  onPipelineComplete,
}: {
  campaignId: string;
  icps: ICP[];
  agents: CampaignAgent[];
  fitmentStates: Record<string, ICPFitmentState>;
  onRunFitment: (icpId: string) => void;
  onRefreshFitment: (icpId: string) => void;
  onPipelineComplete: () => void;
}) {
  const [selectedStages, setSelectedStages] = useState<string[]>([
    "icp_fitment",
    "research",
    "strategy",
  ]);

  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<string | null>(null);
  const [stageResults, setStageResults] = useState<Record<
    string,
    Record<string, unknown>
  > | null>(null);

  const [togglingAgent, setTogglingAgent] = useState<string | null>(null);
  const [agentState, setAgentState] = useState(agents);

  const toggleStage = (stageId: string) => {
    setSelectedStages((current) =>
      current.includes(stageId)
        ? current.filter((id) => id !== stageId)
        : [...current, stageId]
    );
  };

  const runPipeline = async () => {
    if (selectedStages.length === 0) {
      setError("Select at least one stage to run.");
      return;
    }

    setRunning(true);
    setError(null);
    setSummary(null);
    setStageResults(null);

    try {
      /*
       * The backend orders the stages, so the click order here does not
       * matter. Outreach only sends when it is explicitly selected.
       */
      const result = await api.runPipeline(
        campaignId,
        selectedStages,
        selectedStages.includes("outreach")
      );

      setStageResults(result.results);
      setSummary(`Pipeline finished: ${result.stages.join(" → ")}`);

      onPipelineComplete();
    } catch (err) {
      setError(err instanceof Error ? err.message : "The pipeline failed.");
    } finally {
      setRunning(false);
    }
  };

  const toggleAgent = async (agent: CampaignAgent) => {
    setTogglingAgent(agent.agent_type);
    setError(null);

    try {
      const { agent: updated } = await api.updateCampaignAgent(
        campaignId,
        agent.agent_type,
        { enabled: !agent.enabled }
      );

      setAgentState((current) =>
        current.map((item) =>
          item.agent_type === agent.agent_type ? updated : item
        )
      );
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to update the agent."
      );
    } finally {
      setTogglingAgent(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* ============================================================
          PIPELINE
          ============================================================ */}

      <Panel
        title="Run the pipeline"
        description="Pick the stages to run. Each stage feeds the next, and every run is recorded under Activity."
        action={
          <Button variant="primary" onClick={runPipeline} loading={running}>
            <Workflow size={16} />
            {running ? "Running..." : "Run pipeline"}
          </Button>
        }
      >
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {STAGES.map((stage) => {
              const active = selectedStages.includes(stage.id);
              const isOutreach = stage.id === "outreach";

              return (
                <button
                  key={stage.id}
                  type="button"
                  onClick={() => toggleStage(stage.id)}
                  disabled={running}
                  className={`rounded-xl border p-4 text-left transition disabled:opacity-60 ${
                    active
                      ? isOutreach
                        ? "border-amber-500/40 bg-amber-500/10"
                        : "border-indigo-500/40 bg-indigo-500/10"
                      : "border-white/10 bg-white/[0.02] hover:bg-white/5"
                  }`}
                >
                  <p className="text-sm font-medium text-white">
                    {stage.label}
                  </p>

                  <p className="mt-1 text-xs text-gray-500">
                    {stage.description}
                  </p>

                  {isOutreach && active && (
                    <p className="mt-2 text-xs font-medium text-amber-300">
                      Will contact prospects
                    </p>
                  )}
                </button>
              );
            })}
          </div>

          <ErrorNote message={error} />
          <SuccessNote message={summary} />

          {stageResults && (
            <div className="space-y-2 rounded-xl border border-white/10 bg-white/[0.03] p-4">
              {Object.entries(stageResults).map(([stage, result]) => {
                const skipped = Boolean(result.skipped);
                const failed = result.success === false;

                return (
                  <div
                    key={stage}
                    className="flex flex-wrap items-center justify-between gap-2 text-sm"
                  >
                    <span className="font-medium text-gray-200">
                      {agentLabel(stage)}
                    </span>

                    <span className="text-xs text-gray-500">
                      {failed
                        ? String(result.error)
                        : skipped
                          ? String(result.reason)
                          : summarizeStage(result)}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </Panel>

      {/* ============================================================
          ICP FITMENT
          ============================================================ */}

      <Panel
        title="ICP fitment"
        description="Score the prospects at your target companies against a specific ICP."
      >
        {icps.length === 0 ? (
          <EmptyState
            icon={<Bot size={24} />}
            title="No ICPs to score against"
            description="Create an ICP before running the fitment agent."
          />
        ) : (
          <div className="space-y-4">
            {icps.map((icp) => {
              const state = fitmentStates[icp.id];

              return (
                <ICPFitmentAgent
                  key={icp.id}
                  icpName={icp.name}
                  running={state?.running || false}
                  metrics={state?.metrics || null}
                  results={state?.results || []}
                  error={state?.error || null}
                  onRun={() => onRunFitment(icp.id)}
                  onRefresh={() => onRefreshFitment(icp.id)}
                />
              );
            })}
          </div>
        )}
      </Panel>

      {/* ============================================================
          AGENT CONFIGURATION
          ============================================================ */}

      <Panel
        title="Agent configuration"
        description="Disable an agent to keep the pipeline from running it for this campaign."
      >
        <div className="space-y-2">
          {agentState.map((agent) => (
            <div
              key={agent.agent_type}
              className="flex items-center justify-between gap-4 rounded-xl border border-white/10 bg-white/[0.02] p-4"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-white/5">
                  <Bot size={16} className="text-gray-400" />
                </div>

                <div>
                  <p className="text-sm font-medium text-white">
                    {agentLabel(agent.agent_type)}
                  </p>

                  <p className="text-xs text-gray-500">
                    {agent.system_prompt
                      ? "Custom system prompt"
                      : "Default system prompt"}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <Badge value={agent.enabled ? "active" : "paused"} />

                <Button
                  size="sm"
                  onClick={() => toggleAgent(agent)}
                  loading={togglingAgent === agent.agent_type}
                >
                  {agent.enabled ? "Disable" : "Enable"}
                </Button>
              </div>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}

/** Turn a stage result into one readable line. */
function summarizeStage(result: Record<string, unknown>) {
  if (typeof result.succeeded === "number") {
    return `${result.succeeded}/${result.total} succeeded`;
  }

  if (typeof result.prospects_saved === "number") {
    return `${result.prospects_saved} prospects saved`;
  }

  if (typeof result.icps === "number") {
    return `${result.icps} ICP(s) scored`;
  }

  const strategy = result.strategy as
    | { daily_target?: number; campaign_status?: string }
    | undefined;

  if (strategy) {
    return `${strategy.campaign_status} · ${strategy.daily_target} targeted`;
  }

  return "Done";
}

export { STAGES };
