"use client";

import Link from "next/link";
import { ArrowLeft, Settings } from "lucide-react";

import type { Campaign } from "../../../lib/api";

export type CampaignTab =
  | "overview"
  | "companies"
  | "icps"
  | "prospects"
  | "agents"
  | "knowledge"
  | "conversations"
  | "activity";

export const CAMPAIGN_TABS: { id: CampaignTab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "companies", label: "Companies" },
  { id: "icps", label: "ICPs" },
  { id: "prospects", label: "Prospects" },
  { id: "agents", label: "Agents" },
  { id: "knowledge", label: "Knowledge" },
  { id: "conversations", label: "Conversations" },
  { id: "activity", label: "Activity" },
];

export default function CampaignHeader({
  campaign,
  companyName,
  activeTab,
  onTabChange,
}: {
  campaign: Campaign;
  companyName: string;
  activeTab: CampaignTab;
  onTabChange: (tab: CampaignTab) => void;
}) {
  return (
    <div className="mb-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <Link
            href="/dashboard"
            className="mb-3 inline-flex items-center gap-2 text-sm text-gray-500 transition hover:text-white"
          >
            <ArrowLeft size={16} />
            Back to campaigns
          </Link>

          <h1 className="text-3xl font-bold text-white">
            {campaign.objective || "Campaign"}
          </h1>

          {companyName && (
            <p className="mt-1 text-sm text-gray-500">{companyName}</p>
          )}
        </div>

        <Link
          href={`/dashboard/campaigns/${campaign.id}/settings`}
          className="inline-flex h-11 items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-5 text-sm font-medium text-gray-200 transition hover:bg-white/10"
        >
          <Settings size={16} />
          Settings
        </Link>
      </div>

      {/* Tabs */}
      <div className="mt-7 flex gap-1 overflow-x-auto border-b border-white/10">
        {CAMPAIGN_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => onTabChange(tab.id)}
            className={`whitespace-nowrap border-b-2 px-4 py-3 text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? "border-indigo-500 text-white"
                : "border-transparent text-gray-500 hover:text-gray-300"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
    </div>
  );
}
