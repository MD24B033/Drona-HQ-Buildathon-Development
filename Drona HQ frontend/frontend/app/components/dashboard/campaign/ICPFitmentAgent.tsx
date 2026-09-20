"use client";

import { Bot, Play, RefreshCw } from "lucide-react";

import type { ICPFitmentMetrics, ICPMatch } from "../../../lib/api";
import { Badge, Button, ErrorNote, Metric } from "./ui";

export default function ICPFitmentAgent({
  icpName,
  running,
  metrics,
  results,
  error,
  onRun,
  onRefresh,
}: {
  icpName: string;
  running: boolean;
  metrics: ICPFitmentMetrics | null;
  results: ICPMatch[];
  error: string | null;
  onRun: () => void;
  onRefresh: () => void;
}) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.03] p-5">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-500/10">
            <Bot size={17} className="text-indigo-400" />
          </div>

          <div>
            <h3 className="font-semibold text-white">{icpName}</h3>

            <p className="mt-1 text-sm text-gray-500">
              Evaluate every prospect at the target companies against
              this ICP.
            </p>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <Button
            size="sm"
            onClick={onRefresh}
            disabled={running}
            title="Refresh results"
          >
            <RefreshCw size={15} />
          </Button>

          <Button
            size="sm"
            variant="primary"
            onClick={onRun}
            loading={running}
          >
            {!running && <Play size={15} />}
            {running ? "Running" : "Run agent"}
          </Button>
        </div>
      </div>

      {error && (
        <div className="mt-4">
          <ErrorNote message={error} />
        </div>
      )}

      {metrics && (
        <div className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-5">
          <Metric label="Total" value={metrics.total} />
          <Metric
            label="Qualified"
            value={metrics.qualified}
            tone="good"
          />
          <Metric
            label="Disqualified"
            value={metrics.disqualified}
            tone="bad"
          />
          <Metric
            label="Needs review"
            value={metrics.needs_review}
            tone="warn"
          />
          <Metric label="Failed" value={metrics.failed} />
        </div>
      )}

      {results.length > 0 && (
        <div className="mt-5 border-t border-white/10 pt-4">
          <p className="mb-3 text-xs uppercase tracking-wide text-gray-500">
            Top evaluations
          </p>

          <div className="space-y-2">
            {results.slice(0, 5).map((result) => (
              <div
                key={result.id}
                className="flex items-center justify-between gap-4 rounded-lg bg-white/[0.03] px-3 py-2"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm text-gray-200">
                    {result.prospects?.full_name || result.prospect_id}
                  </p>

                  <p className="truncate text-xs text-gray-500">
                    {[
                      result.prospects?.current_title,
                      result.prospects?.companies?.name,
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                </div>

                <div className="flex shrink-0 items-center gap-3">
                  <span className="text-sm font-semibold text-white">
                    {Number(result.match_score).toFixed(0)}
                  </span>

                  <Badge value={result.decision} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
