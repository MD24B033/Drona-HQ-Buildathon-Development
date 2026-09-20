"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Loader2,
  Target,
} from "lucide-react";

import { api } from "../../lib/api";
import { getSession } from "../../lib/supabase/session";

type Step = 1 | 2;

/** Turn a comma-separated input into a clean array of values. */
const toList = (value: string) =>
  value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);

export default function CreateCampaign() {
  const router = useRouter();

  const [step, setStep] = useState<Step>(1);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  /*
   * Campaign
   */
  const [campaign, setCampaign] = useState({
    objective: "",
    geography: "",
    target_personas: "",
    agent_instructions: "",
    campaign_specific_knowledge: "",
    outreach_strategy: "",
    qualification_criteria: "",
    daily_limits: "50",
  });

  /*
   * First ICP
   */
  const [icp, setIcp] = useState({
    name: "",
    description: "",
    industries: "",
    company_sizes: "",
    job_titles: "",
    technologies: "",
    other_criteria: "",
  });

  const updateCampaign = (
    field: keyof typeof campaign,
    value: string
  ) => {
    setCampaign((current) => ({
      ...current,
      [field]: value,
    }));
  };

  const updateIcp = (
    field: keyof typeof icp,
    value: string
  ) => {
    setIcp((current) => ({
      ...current,
      [field]: value,
    }));
  };

  const nextStep = () => {
    setError("");

    if (!campaign.objective.trim()) {
      setError("Please enter a campaign objective.");
      return;
    }

    if (!campaign.geography.trim()) {
      setError("Please enter at least one target geography.");
      return;
    }

    if (!campaign.target_personas.trim()) {
      setError("Please enter at least one target persona.");
      return;
    }

    setStep(2);
  };

  const createCampaign = async () => {
    setError("");

    if (!icp.name.trim()) {
      setError("Please give your ICP a name.");
      return;
    }

    if (!icp.description.trim()) {
      setError("Please describe your ideal customer.");
      return;
    }

    setSaving(true);

    try {
      const session = await getSession();

      if (!session) {
        router.replace("/auth");
        return;
      }

      /*
       * The backend creates the campaign and its first ICP together,
       * and rolls the campaign back if the ICP cannot be saved.
       */
      const { campaign: created } = await api.createCampaign({
        objective: campaign.objective.trim(),

        geography: toList(campaign.geography),

        target_personas: toList(campaign.target_personas),

        agent_instructions:
          campaign.agent_instructions.trim() ||
          "Identify qualified prospects matching the campaign ICP and personalize outreach based on available company and prospect information.",

        campaign_specific_knowledge:
          campaign.campaign_specific_knowledge.trim() || null,

        outreach_strategy:
          campaign.outreach_strategy.trim() ||
          "Use personalized, value-driven outreach based on the prospect's company, role, and relevant business context.",

        qualification_criteria: toList(
          campaign.qualification_criteria
        ),

        daily_limits: Number(campaign.daily_limits) || 50,

        icp: {
          name: icp.name.trim(),
          description: icp.description.trim(),
          criteria: {
            industries: toList(icp.industries),
            company_sizes: toList(icp.company_sizes),
            job_titles: toList(icp.job_titles),
            technologies: toList(icp.technologies),
            other: icp.other_criteria.trim(),
          },
        },
      });

      router.replace(`/dashboard/campaigns/${created.id}`);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(
          "Something went wrong while creating the campaign."
        );
      }

      setSaving(false);
    }
  };

  return (
    <main className="min-h-screen bg-[#070b14] text-white px-4 py-10">

      <div className="max-w-3xl mx-auto">

        {/* Back */}
        <button
          type="button"
          onClick={() => router.push("/dashboard")}
          className="flex items-center gap-2 text-sm text-gray-500 hover:text-white transition-colors mb-8"
        >
          <ArrowLeft size={16} />
          Back to campaigns
        </button>

        {/* Header */}
        <div className="mb-8">

          <p className="text-sm text-indigo-400 font-medium mb-2">
            New campaign
          </p>

          <h1 className="text-3xl font-bold">
            Create a sales campaign
          </h1>

          <p className="text-gray-400 mt-2">
            Configure your campaign and define the
            customers your sales automation should target.
          </p>

        </div>

        {/* Progress */}
        <div className="flex items-center gap-3 mb-8">

          <div
            className={`flex items-center gap-2 ${
              step >= 1
                ? "text-white"
                : "text-gray-600"
            }`}
          >
            <div
              className={`h-8 w-8 rounded-full flex items-center justify-center text-sm ${
                step >= 1
                  ? "bg-indigo-500"
                  : "bg-white/10"
              }`}
            >
              1
            </div>

            <span className="text-sm">
              Campaign
            </span>
          </div>

          <div className="h-px flex-1 bg-white/10" />

          <div
            className={`flex items-center gap-2 ${
              step >= 2
                ? "text-white"
                : "text-gray-600"
            }`}
          >
            <div
              className={`h-8 w-8 rounded-full flex items-center justify-center text-sm ${
                step >= 2
                  ? "bg-indigo-500"
                  : "bg-white/10"
              }`}
            >
              {step > 2 ? (
                <Check size={15} />
              ) : (
                "2"
              )}
            </div>

            <span className="text-sm">
              First ICP
            </span>
          </div>

        </div>

        {/* Error */}
        {error && (
          <div className="mb-6 rounded-2xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}

        {/* STEP 1 */}
        {step === 1 && (
          <motion.div
            initial={{
              opacity: 0,
              x: 20,
            }}
            animate={{
              opacity: 1,
              x: 0,
            }}
            className="rounded-[28px] border border-white/10 bg-white/5 backdrop-blur-2xl p-7 md:p-9"
          >

            <h2 className="text-xl font-semibold mb-1">
              Campaign configuration
            </h2>

            <p className="text-sm text-gray-500 mb-7">
              Define the purpose and operating rules
              for this campaign.
            </p>

            <div className="space-y-6">

              {/* Objective */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Campaign objective
                </label>

                <input
                  required
                  value={campaign.objective}
                  onChange={(e) =>
                    updateCampaign(
                      "objective",
                      e.target.value
                    )
                  }
                  placeholder="e.g. Generate qualified SaaS leads"
                  className="w-full h-14 rounded-2xl bg-white/5 border border-white/10 px-5 outline-none focus:border-indigo-500 transition-all placeholder:text-gray-600"
                />
              </div>

              {/* Geography */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Target geography
                </label>

                <input
                  required
                  value={campaign.geography}
                  onChange={(e) =>
                    updateCampaign(
                      "geography",
                      e.target.value
                    )
                  }
                  placeholder="e.g. United States, Canada, United Kingdom"
                  className="w-full h-14 rounded-2xl bg-white/5 border border-white/10 px-5 outline-none focus:border-indigo-500 transition-all placeholder:text-gray-600"
                />

                <p className="text-xs text-gray-600 mt-2">
                  Separate multiple locations with commas.
                </p>
              </div>

              {/* Personas */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Target personas
                </label>

                <input
                  required
                  value={campaign.target_personas}
                  onChange={(e) =>
                    updateCampaign(
                      "target_personas",
                      e.target.value
                    )
                  }
                  placeholder="e.g. VP Sales, CRO, Head of Growth"
                  className="w-full h-14 rounded-2xl bg-white/5 border border-white/10 px-5 outline-none focus:border-indigo-500 transition-all placeholder:text-gray-600"
                />

                <p className="text-xs text-gray-600 mt-2">
                  Separate multiple roles with commas.
                </p>
              </div>

              {/* Outreach Strategy */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Outreach strategy
                </label>

                <textarea
                  rows={4}
                  value={campaign.outreach_strategy}
                  onChange={(e) =>
                    updateCampaign(
                      "outreach_strategy",
                      e.target.value
                    )
                  }
                  placeholder="Describe how prospects should be approached..."
                  className="w-full rounded-2xl bg-white/5 border border-white/10 px-5 py-4 outline-none focus:border-indigo-500 transition-all placeholder:text-gray-600 resize-none"
                />
              </div>

              {/* Agent Instructions */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Agent instructions
                </label>

                <textarea
                  rows={4}
                  value={campaign.agent_instructions}
                  onChange={(e) =>
                    updateCampaign(
                      "agent_instructions",
                      e.target.value
                    )
                  }
                  placeholder="Instructions for the sales automation agent..."
                  className="w-full rounded-2xl bg-white/5 border border-white/10 px-5 py-4 outline-none focus:border-indigo-500 transition-all placeholder:text-gray-600 resize-none"
                />
              </div>

              {/* Knowledge */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Campaign-specific knowledge
                </label>

                <textarea
                  rows={4}
                  value={
                    campaign.campaign_specific_knowledge
                  }
                  onChange={(e) =>
                    updateCampaign(
                      "campaign_specific_knowledge",
                      e.target.value
                    )
                  }
                  placeholder="Products, pricing, differentiators, case studies, sales context..."
                  className="w-full rounded-2xl bg-white/5 border border-white/10 px-5 py-4 outline-none focus:border-indigo-500 transition-all placeholder:text-gray-600 resize-none"
                />
              </div>

              {/* Qualification */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Qualification criteria
                </label>

                <input
                  value={
                    campaign.qualification_criteria
                  }
                  onChange={(e) =>
                    updateCampaign(
                      "qualification_criteria",
                      e.target.value
                    )
                  }
                  placeholder="e.g. Has budget, Uses Salesforce, 50+ employees"
                  className="w-full h-14 rounded-2xl bg-white/5 border border-white/10 px-5 outline-none focus:border-indigo-500 transition-all placeholder:text-gray-600"
                />

                <p className="text-xs text-gray-600 mt-2">
                  Separate criteria with commas.
                </p>
              </div>

              {/* Daily limit */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Daily outreach limit
                </label>

                <input
                  type="number"
                  min={1}
                  max={10000}
                  value={campaign.daily_limits}
                  onChange={(e) =>
                    updateCampaign(
                      "daily_limits",
                      e.target.value
                    )
                  }
                  className="w-full h-14 rounded-2xl bg-white/5 border border-white/10 px-5 outline-none focus:border-indigo-500 transition-all"
                />
              </div>

              {/* Next */}
              <button
                type="button"
                onClick={nextStep}
                className="w-full h-14 rounded-2xl bg-gradient-to-r from-indigo-500 to-cyan-500 font-semibold flex items-center justify-center gap-2 hover:opacity-90 transition-all"
              >
                Define first ICP
                <ArrowRight size={18} />
              </button>

            </div>
          </motion.div>
        )}

        {/* STEP 2 */}
        {step === 2 && (
          <motion.div
            initial={{
              opacity: 0,
              x: 20,
            }}
            animate={{
              opacity: 1,
              x: 0,
            }}
            className="rounded-[28px] border border-white/10 bg-white/5 backdrop-blur-2xl p-7 md:p-9"
          >

            <div className="flex items-center gap-4 mb-7">

              <div className="h-12 w-12 rounded-2xl bg-indigo-500/10 flex items-center justify-center">
                <Target
                  size={23}
                  className="text-indigo-400"
                />
              </div>

              <div>
                <h2 className="text-xl font-semibold">
                  Define your first ICP
                </h2>

                <p className="text-sm text-gray-500">
                  Every campaign must have at least one
                  Ideal Customer Profile.
                </p>
              </div>

            </div>

            <div className="space-y-6">

              {/* ICP Name */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  ICP name
                </label>

                <input
                  required
                  value={icp.name}
                  onChange={(e) =>
                    updateIcp(
                      "name",
                      e.target.value
                    )
                  }
                  placeholder="e.g. B2B SaaS Companies"
                  className="w-full h-14 rounded-2xl bg-white/5 border border-white/10 px-5 outline-none focus:border-indigo-500 transition-all placeholder:text-gray-600"
                />
              </div>

              {/* Description */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  ICP description
                </label>

                <textarea
                  required
                  rows={4}
                  value={icp.description}
                  onChange={(e) =>
                    updateIcp(
                      "description",
                      e.target.value
                    )
                  }
                  placeholder="Describe the type of company that is an ideal customer..."
                  className="w-full rounded-2xl bg-white/5 border border-white/10 px-5 py-4 outline-none focus:border-indigo-500 transition-all placeholder:text-gray-600 resize-none"
                />
              </div>

              {/* Industries */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Industries
                </label>

                <input
                  value={icp.industries}
                  onChange={(e) =>
                    updateIcp(
                      "industries",
                      e.target.value
                    )
                  }
                  placeholder="e.g. SaaS, FinTech, Cybersecurity"
                  className="w-full h-14 rounded-2xl bg-white/5 border border-white/10 px-5 outline-none focus:border-indigo-500 transition-all placeholder:text-gray-600"
                />
              </div>

              {/* Company sizes */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Company sizes
                </label>

                <input
                  value={icp.company_sizes}
                  onChange={(e) =>
                    updateIcp(
                      "company_sizes",
                      e.target.value
                    )
                  }
                  placeholder="e.g. 51-200, 201-500, 500+"
                  className="w-full h-14 rounded-2xl bg-white/5 border border-white/10 px-5 outline-none focus:border-indigo-500 transition-all placeholder:text-gray-600"
                />
              </div>

              {/* Job titles */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Target job titles
                </label>

                <input
                  value={icp.job_titles}
                  onChange={(e) =>
                    updateIcp(
                      "job_titles",
                      e.target.value
                    )
                  }
                  placeholder="e.g. CEO, VP Sales, CRO, Head of Growth"
                  className="w-full h-14 rounded-2xl bg-white/5 border border-white/10 px-5 outline-none focus:border-indigo-500 transition-all placeholder:text-gray-600"
                />
              </div>

              {/* Technologies */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Technologies
                </label>

                <input
                  value={icp.technologies}
                  onChange={(e) =>
                    updateIcp(
                      "technologies",
                      e.target.value
                    )
                  }
                  placeholder="e.g. Salesforce, HubSpot, AWS"
                  className="w-full h-14 rounded-2xl bg-white/5 border border-white/10 px-5 outline-none focus:border-indigo-500 transition-all placeholder:text-gray-600"
                />
              </div>

              {/* Other */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Additional criteria
                </label>

                <textarea
                  rows={4}
                  value={icp.other_criteria}
                  onChange={(e) =>
                    updateIcp(
                      "other_criteria",
                      e.target.value
                    )
                  }
                  placeholder="Any additional characteristics that define this ICP..."
                  className="w-full rounded-2xl bg-white/5 border border-white/10 px-5 py-4 outline-none focus:border-indigo-500 transition-all placeholder:text-gray-600 resize-none"
                />
              </div>

              {/* Buttons */}
              <div className="flex gap-3">

                <button
                  type="button"
                  disabled={saving}
                  onClick={() => {
                    setError("");
                    setStep(1);
                  }}
                  className="h-14 px-6 rounded-2xl border border-white/10 bg-white/5 hover:bg-white/10 transition-all flex items-center gap-2"
                >
                  <ArrowLeft size={17} />
                  Back
                </button>

                <button
                  type="button"
                  disabled={saving}
                  onClick={createCampaign}
                  className="flex-1 h-14 rounded-2xl bg-gradient-to-r from-indigo-500 to-cyan-500 font-semibold flex items-center justify-center gap-2 hover:opacity-90 transition-all disabled:opacity-50"
                >
                  {saving ? (
                    <>
                      <Loader2
                        size={18}
                        className="animate-spin"
                      />
                      Creating campaign...
                    </>
                  ) : (
                    <>
                      <Check size={18} />
                      Create campaign
                    </>
                  )}
                </button>

              </div>

            </div>
          </motion.div>
        )}

      </div>
    </main>
  );
}