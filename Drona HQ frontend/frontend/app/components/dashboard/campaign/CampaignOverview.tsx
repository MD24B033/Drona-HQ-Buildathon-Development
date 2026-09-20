"use client";

import {
  Building2,
  CheckCircle2,
  FileText,
  Globe2,
  MessageSquare,
  Microscope,
  Send,
  Target,
  Users,
} from "lucide-react";

import type { Campaign, CampaignStats } from "../../../lib/api";
import { Panel } from "./ui";

export default function CampaignOverview({
  campaign,
  stats,
}: {
  campaign: Campaign;
  stats: CampaignStats;
}) {
  /*
   * The funnel, in the order the agents actually run.
   */
  const cards = [
    { label: "Target companies", value: stats.companies, icon: Building2 },
    { label: "ICPs", value: stats.icps, icon: Target },
    {
      label: "Prospects evaluated",
      value: stats.evaluated_prospects,
      icon: Users,
    },
    {
      label: "Qualified",
      value: stats.qualified_prospects,
      icon: CheckCircle2,
    },
    {
      label: "Researched",
      value: stats.researched_prospects,
      icon: Microscope,
    },
    { label: "Outreach planned", value: stats.planned_outreach, icon: Send },
    {
      label: "Conversations",
      value: stats.conversations,
      icon: MessageSquare,
    },
    {
      label: "Knowledge docs",
      value: stats.knowledge_documents,
      icon: FileText,
    },
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {cards.map((card) => {
          const Icon = card.icon;

          return (
            <div
              key={card.label}
              className="rounded-2xl border border-white/10 bg-white/5 p-5"
            >
              <div className="mb-4 flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-500/10">
                <Icon size={17} className="text-indigo-400" />
              </div>

              <p className="text-sm text-gray-500">{card.label}</p>

              <p className="mt-1 text-2xl font-semibold text-white">
                {card.value}
              </p>
            </div>
          );
        })}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Targeting">
          <div className="space-y-5">
            <TagRow
              icon={<Globe2 size={15} />}
              label="Geography"
              values={campaign.geography}
            />

            <TagRow
              icon={<Users size={15} />}
              label="Target personas"
              values={campaign.target_personas}
            />

            <TagRow
              icon={<CheckCircle2 size={15} />}
              label="Qualification criteria"
              values={campaign.qualification_criteria}
            />

            <div>
              <p className="mb-2 flex items-center gap-2 text-xs uppercase tracking-wide text-gray-500">
                <Send size={15} />
                Daily outreach limit
              </p>

              <p className="text-sm text-gray-200">
                {campaign.daily_limits} messages per day
              </p>
            </div>
          </div>
        </Panel>

        <Panel title="Agent instructions">
          <div className="space-y-5">
            <Paragraph
              label="Outreach strategy"
              value={campaign.outreach_strategy}
            />

            <Paragraph
              label="Agent instructions"
              value={campaign.agent_instructions}
            />

            <Paragraph
              label="Campaign knowledge"
              value={campaign.campaign_specific_knowledge}
            />
          </div>
        </Panel>
      </div>
    </div>
  );
}

function TagRow({
  icon,
  label,
  values,
}: {
  icon: React.ReactNode;
  label: string;
  values: string[] | null;
}) {
  return (
    <div>
      <p className="mb-2 flex items-center gap-2 text-xs uppercase tracking-wide text-gray-500">
        {icon}
        {label}
      </p>

      {values && values.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {values.map((value) => (
            <span
              key={value}
              className="rounded-lg border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-gray-300"
            >
              {value}
            </span>
          ))}
        </div>
      ) : (
        <p className="text-sm text-gray-600">Not set</p>
      )}
    </div>
  );
}

function Paragraph({
  label,
  value,
}: {
  label: string;
  value: string | null;
}) {
  return (
    <div>
      <p className="mb-2 text-xs uppercase tracking-wide text-gray-500">
        {label}
      </p>

      <p className="whitespace-pre-wrap text-sm leading-relaxed text-gray-300">
        {value || "Not set"}
      </p>
    </div>
  );
}
