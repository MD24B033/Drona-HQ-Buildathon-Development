"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Save, Trash2 } from "lucide-react";

import { api, type Campaign } from "../../../../lib/api";
import {
  Button,
  ErrorNote,
  Field,
  Panel,
  Spinner,
  SuccessNote,
  TextArea,
  TextInput,
} from "../../../../components/dashboard/campaign/ui";

const toList = (value: string) =>
  value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);

export default function CampaignSettingsPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();

  const campaignId = params.id;

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);

  const [form, setForm] = useState({
    objective: "",
    geography: "",
    target_personas: "",
    qualification_criteria: "",
    outreach_strategy: "",
    agent_instructions: "",
    campaign_specific_knowledge: "",
    daily_limits: "50",
    daily_target: "",
  });

  const hydrate = useCallback((campaign: Campaign) => {
    const channelConfig = (campaign.channel_configuration || {}) as {
      daily_target?: number;
    };

    setForm({
      objective: campaign.objective || "",
      geography: (campaign.geography || []).join(", "),
      target_personas: (campaign.target_personas || []).join(", "),
      qualification_criteria: (
        campaign.qualification_criteria || []
      ).join(", "),
      outreach_strategy: campaign.outreach_strategy || "",
      agent_instructions: campaign.agent_instructions || "",
      campaign_specific_knowledge:
        campaign.campaign_specific_knowledge || "",
      daily_limits: String(campaign.daily_limits ?? 50),
      daily_target:
        channelConfig.daily_target !== undefined
          ? String(channelConfig.daily_target)
          : "",
    });
  }, []);

  useEffect(() => {
    const load = async () => {
      try {
        const { campaign } = await api.getCampaign(campaignId);

        hydrate(campaign);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load the campaign."
        );
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [campaignId, hydrate]);

  const update = (field: keyof typeof form, value: string) =>
    setForm((current) => ({ ...current, [field]: value }));

  const save = async () => {
    if (!form.objective.trim()) {
      setError("A campaign needs an objective.");
      return;
    }

    setSaving(true);
    setError(null);
    setSaved(null);

    try {
      const { campaign } = await api.updateCampaign(campaignId, {
        objective: form.objective.trim(),
        geography: toList(form.geography),
        target_personas: toList(form.target_personas),
        qualification_criteria: toList(form.qualification_criteria),
        outreach_strategy: form.outreach_strategy.trim(),
        agent_instructions: form.agent_instructions.trim(),
        campaign_specific_knowledge:
          form.campaign_specific_knowledge.trim() || null,
        daily_limits: Number(form.daily_limits) || 50,
        channel_configuration: form.daily_target
          ? { daily_target: Number(form.daily_target) }
          : {},
      });

      hydrate(campaign);
      setSaved("Campaign settings saved.");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to save changes."
      );
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    setDeleting(true);
    setError(null);

    try {
      await api.deleteCampaign(campaignId);

      router.replace("/dashboard");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to delete the campaign."
      );

      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#070b14]">
        <Spinner label="Loading settings..." />
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

        <h1 className="mb-8 text-3xl font-bold">Campaign settings</h1>

        <div className="space-y-6">
          <Panel
            title="Targeting"
            description="What this campaign is trying to achieve, and who it targets."
          >
            <div className="space-y-5">
              <Field label="Objective">
                <TextInput
                  value={form.objective}
                  onChange={(value) => update("objective", value)}
                  placeholder="Generate qualified SaaS leads"
                />
              </Field>

              <Field
                label="Target geography"
                hint="Separate multiple locations with commas."
              >
                <TextInput
                  value={form.geography}
                  onChange={(value) => update("geography", value)}
                  placeholder="United States, Canada"
                />
              </Field>

              <Field
                label="Target personas"
                hint="Separate multiple roles with commas."
              >
                <TextInput
                  value={form.target_personas}
                  onChange={(value) => update("target_personas", value)}
                  placeholder="VP Sales, CRO, Head of Growth"
                />
              </Field>

              <Field
                label="Qualification criteria"
                hint="Separate criteria with commas."
              >
                <TextInput
                  value={form.qualification_criteria}
                  onChange={(value) =>
                    update("qualification_criteria", value)
                  }
                  placeholder="Has budget, 50+ employees"
                />
              </Field>
            </div>
          </Panel>

          <Panel
            title="Agent behaviour"
            description="These fields are given to every agent that runs for this campaign."
          >
            <div className="space-y-5">
              <Field label="Outreach strategy">
                <TextArea
                  value={form.outreach_strategy}
                  onChange={(value) =>
                    update("outreach_strategy", value)
                  }
                  placeholder="How prospects should be approached..."
                />
              </Field>

              <Field label="Agent instructions">
                <TextArea
                  value={form.agent_instructions}
                  onChange={(value) =>
                    update("agent_instructions", value)
                  }
                  placeholder="Instructions for the sales automation agents..."
                />
              </Field>

              <Field
                label="Campaign-specific knowledge"
                hint="For longer material, use the Knowledge tab so it gets embedded and retrieved."
              >
                <TextArea
                  value={form.campaign_specific_knowledge}
                  onChange={(value) =>
                    update("campaign_specific_knowledge", value)
                  }
                  placeholder="Products, pricing, differentiators..."
                />
              </Field>
            </div>
          </Panel>

          <Panel
            title="Limits"
            description="Hard caps the strategy agent cannot exceed."
          >
            <div className="grid gap-5 sm:grid-cols-2">
              <Field
                label="Daily outreach limit"
                hint="Maximum messages sent in any 24 hours."
              >
                <TextInput
                  type="number"
                  value={form.daily_limits}
                  onChange={(value) => update("daily_limits", value)}
                />
              </Field>

              <Field
                label="Daily target"
                hint="How many prospects the strategy agent should aim for. Leave blank for the default."
              >
                <TextInput
                  type="number"
                  value={form.daily_target}
                  onChange={(value) => update("daily_target", value)}
                  placeholder="20"
                />
              </Field>
            </div>
          </Panel>

          <ErrorNote message={error} />
          <SuccessNote message={saved} />

          <div className="flex justify-end">
            <Button variant="primary" onClick={save} loading={saving}>
              <Save size={16} />
              Save changes
            </Button>
          </div>

          <Panel
            title="Danger zone"
            description="Deleting a campaign removes its ICPs, prospect scores, research, strategies and conversations."
          >
            {confirmingDelete ? (
              <div className="flex flex-wrap items-center gap-3">
                <p className="text-sm text-red-300">
                  This cannot be undone. Delete this campaign?
                </p>

                <Button
                  variant="danger"
                  onClick={remove}
                  loading={deleting}
                >
                  Yes, delete it
                </Button>

                <Button onClick={() => setConfirmingDelete(false)}>
                  Cancel
                </Button>
              </div>
            ) : (
              <Button
                variant="danger"
                onClick={() => setConfirmingDelete(true)}
              >
                <Trash2 size={16} />
                Delete campaign
              </Button>
            )}
          </Panel>
        </div>
      </div>
    </main>
  );
}
