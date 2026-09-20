"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";

import {
  api,
  type ICP,
  type ICPFitmentMetrics,
  type ICPMatch,
} from "../../../../../lib/api";
import ICPForm, {
  type ICPFormValues,
} from "../../../../../components/dashboard/campaign/ICPForm";
import {
  Badge,
  ErrorNote,
  Metric,
  Panel,
  Spinner,
  formatDate,
} from "../../../../../components/dashboard/campaign/ui";

export default function ICPDetailPage() {
  const params = useParams<{ id: string; icpId: string }>();
  const router = useRouter();

  const campaignId = params.id;
  const icpId = params.icpId;

  const [icp, setIcp] = useState<ICP | null>(null);
  const [metrics, setMetrics] = useState<ICPFitmentMetrics | null>(null);
  const [results, setResults] = useState<ICPMatch[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const { icp } = await api.getICP(campaignId, icpId);

        setIcp(icp);

        /* Scores are informational here, so a failure is not fatal. */
        try {
          const fitment = await api.getICPFitmentResults(icpId);

          setMetrics(fitment.metrics);
          setResults(fitment.results);
        } catch {
          setMetrics(null);
        }
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Unable to load the ICP."
        );
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [campaignId, icpId]);

  const save = async (values: ICPFormValues) => {
    const { icp } = await api.updateICP(campaignId, icpId, values);

    setIcp(icp);
    setNotice("ICP saved.");
  };

  const remove = async () => {
    await api.deleteICP(campaignId, icpId);

    router.replace(`/dashboard/campaigns/${campaignId}`);
  };

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#070b14]">
        <Spinner label="Loading ICP..." />
      </main>
    );
  }

  if (error || !icp) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#070b14] px-6">
        <div className="w-full max-w-md">
          <ErrorNote message={error || "ICP not found."} />
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#070b14] text-white">
      <div className="mx-auto max-w-3xl px-6 py-8">
        <Link
          href={`/dashboard/campaigns/${campaignId}`}
          className="mb-6 inline-flex items-center gap-2 text-sm text-gray-500 transition hover:text-white"
        >
          <ArrowLeft size={16} />
          Back to campaign
        </Link>

        <h1 className="mb-8 text-3xl font-bold">{icp.name}</h1>

        <div className="space-y-6">
          {metrics && metrics.total > 0 && (
            <Panel
              title="Fitment results"
              description="How the prospects at this campaign's target companies scored."
            >
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <Metric label="Evaluated" value={metrics.total} />
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
              </div>

              <div className="mt-5 space-y-2">
                {results.slice(0, 10).map((result) => (
                  <div
                    key={result.id}
                    className="rounded-xl border border-white/10 bg-white/[0.02] p-4"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-white">
                          {result.prospects?.full_name ||
                            result.prospect_id}
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
                        <span className="text-sm font-semibold">
                          {Number(result.match_score).toFixed(0)}
                        </span>

                        <Badge value={result.decision} />
                      </div>
                    </div>

                    {result.reasoning && (
                      <p className="mt-2 text-sm leading-relaxed text-gray-400">
                        {result.reasoning}
                      </p>
                    )}

                    <p className="mt-2 text-xs text-gray-600">
                      Evaluated {formatDate(result.evaluated_at)}
                    </p>
                  </div>
                ))}
              </div>
            </Panel>
          )}

          <ICPForm
            icp={icp}
            submitLabel="Save ICP"
            onSubmit={save}
            onDelete={remove}
            notice={notice}
          />
        </div>
      </div>
    </main>
  );
}
