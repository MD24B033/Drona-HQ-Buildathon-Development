"use client";

import Link from "next/link";
import { ArrowRight, Plus, Target } from "lucide-react";

import type { ICP } from "../../../lib/api";
import { EmptyState, Panel } from "./ui";

export default function CampaignICPs({
  campaignId,
  icps,
}: {
  campaignId: string;
  icps: ICP[];
}) {
  return (
    <Panel
      title="Ideal customer profiles"
      description="Each ICP is scored independently against the campaign's prospects."
      action={
        <Link
          href={`/dashboard/campaigns/${campaignId}/icps/new`}
          className="inline-flex h-9 items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-500 to-cyan-500 px-4 text-sm font-medium text-white transition hover:opacity-90"
        >
          <Plus size={15} />
          Add ICP
        </Link>
      }
    >
      {icps.length === 0 ? (
        <EmptyState
          icon={<Target size={24} />}
          title="No ICPs yet"
          description="Create an ICP to define who this campaign should target."
          action={
            <Link
              href={`/dashboard/campaigns/${campaignId}/icps/new`}
              className="inline-flex h-11 items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-500 to-cyan-500 px-5 text-sm font-medium text-white"
            >
              <Plus size={16} />
              Create ICP
            </Link>
          }
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {icps.map((icp) => (
            <Link
              key={icp.id}
              href={`/dashboard/campaigns/${campaignId}/icps/${icp.id}`}
              className="group rounded-xl border border-white/10 bg-white/[0.03] p-5 transition hover:border-indigo-500/30 hover:bg-white/[0.06]"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-indigo-500/10">
                    <Target size={17} className="text-indigo-400" />
                  </div>

                  <div>
                    <h3 className="font-semibold text-white">{icp.name}</h3>

                    {icp.description && (
                      <p className="mt-1 line-clamp-2 text-sm text-gray-500">
                        {icp.description}
                      </p>
                    )}
                  </div>
                </div>

                <ArrowRight
                  size={17}
                  className="shrink-0 text-gray-600 transition group-hover:translate-x-1 group-hover:text-white"
                />
              </div>

              <CriteriaTags criteria={icp.criteria} />
            </Link>
          ))}
        </div>
      )}
    </Panel>
  );
}

function CriteriaTags({
  criteria,
}: {
  criteria: Record<string, unknown>;
}) {
  /* Only the list-shaped criteria make sensible chips. */
  const tags = Object.entries(criteria || {})
    .filter(([, value]) => Array.isArray(value) && value.length > 0)
    .flatMap(([key, value]) =>
      (value as unknown[]).slice(0, 3).map((item) => ({
        key: `${key}-${String(item)}`,
        label: String(item),
      }))
    )
    .slice(0, 6);

  if (tags.length === 0) return null;

  return (
    <div className="mt-4 flex flex-wrap gap-2 border-t border-white/10 pt-4">
      {tags.map((tag) => (
        <span
          key={tag.key}
          className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-xs text-gray-400"
        >
          {tag.label}
        </span>
      ))}
    </div>
  );
}
