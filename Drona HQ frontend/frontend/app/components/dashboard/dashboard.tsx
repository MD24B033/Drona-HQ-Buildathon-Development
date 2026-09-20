"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  Plus,
  Target,
  Megaphone,
  Loader2,
  CalendarDays,
  ArrowRight,
} from "lucide-react";

import { api, type Campaign } from "../../lib/api";
import { getSession, signOut } from "../../lib/supabase/session";

export default function DashboardPage() {
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [companyName, setCompanyName] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const loadDashboard = async () => {
      const session = await getSession();

      if (!session) {
        router.replace("/auth");
        return;
      }

      try {
        const { profile } = await api.getProfile();

        // Onboarding has to come first.
        if (!profile.onboarding_completed) {
          router.replace("/onboarding");
          return;
        }

        setCompanyName(profile.company_name || "Your Company");

        const { campaigns } = await api.listCampaigns();

        setCampaigns(campaigns);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load your campaigns."
        );
      } finally {
        setLoading(false);
      }
    };

    loadDashboard();
  }, [router]);

  const formatDate = (date: string) => {
    return new Date(date).toLocaleDateString(
      undefined,
      {
        month: "short",
        day: "numeric",
        year: "numeric",
      }
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#070b14] flex items-center justify-center text-white">
        <div className="flex items-center gap-3 text-gray-400">
          <Loader2
            size={18}
            className="animate-spin"
          />
          Loading campaigns...
        </div>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-[#070b14] text-white">

      {/* Header */}
      <header className="border-b border-white/10">
        <div className="max-w-7xl mx-auto px-6 py-5 flex items-center justify-between">

          <div>
            <p className="text-sm text-gray-500">
              Sales automation
            </p>

            <h1 className="text-xl font-semibold">
              {companyName}
            </h1>
          </div>

          <div className="flex items-center gap-5">
            <button
              onClick={() =>
                router.push("/onboarding?edit=1")
              }
              className="text-sm text-gray-400 hover:text-white transition-colors"
            >
              Company settings
            </button>

            <button
              onClick={() => signOut()}
              className="text-sm text-gray-400 hover:text-white transition-colors"
            >
              Sign out
            </button>
          </div>

        </div>
      </header>

      {error && (
        <div className="max-w-7xl mx-auto px-6 pt-6">
          <div className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        </div>
      )}

      {/* Main */}
      <div className="max-w-7xl mx-auto px-6 py-10">

        {/* Heading */}
        <motion.div
          initial={{
            opacity: 0,
            y: 10,
          }}
          animate={{
            opacity: 1,
            y: 0,
          }}
          className="flex flex-col md:flex-row md:items-end md:justify-between gap-5 mb-10"
        >

          <div>
            <h2 className="text-3xl font-bold">
              Campaigns
            </h2>

            <p className="text-gray-400 mt-2">
              Create and manage your automated sales
              campaigns.
            </p>
          </div>

          <button
            onClick={() =>
              router.push(
                "/dashboard/campaigns/new"
              )
            }
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-500 to-cyan-500 px-5 py-3 font-semibold text-sm hover:opacity-90 transition-all"
          >
            <Plus size={18} />
            Create campaign
          </button>

        </motion.div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-10">

          {/* Campaign count */}
          <div className="rounded-2xl border border-white/10 bg-white/5 p-6">

            <div className="flex items-center gap-3 mb-4">

              <div className="h-10 w-10 rounded-xl bg-indigo-500/10 flex items-center justify-center">
                <Megaphone
                  size={19}
                  className="text-indigo-400"
                />
              </div>

              <span className="text-sm text-gray-400">
                Total campaigns
              </span>

            </div>

            <p className="text-3xl font-bold">
              {campaigns.length}
            </p>

          </div>

          {/* ICP */}
          <div className="rounded-2xl border border-white/10 bg-white/5 p-6">

            <div className="flex items-center gap-3 mb-4">

              <div className="h-10 w-10 rounded-xl bg-cyan-500/10 flex items-center justify-center">
                <Target
                  size={19}
                  className="text-cyan-400"
                />
              </div>

              <span className="text-sm text-gray-400">
                Ideal customer profiles
              </span>

            </div>

            <p className="text-3xl font-bold">
              {campaigns.reduce(
                (total, campaign) =>
                  total + (campaign.icp_count || 0),
                0
              )}
            </p>

            <p className="text-sm text-gray-500 mt-1">
              across{" "}
              {campaigns.reduce(
                (total, campaign) =>
                  total + (campaign.company_count || 0),
                0
              )}{" "}
              target companies
            </p>

          </div>

          {/* Latest */}
          <div className="rounded-2xl border border-white/10 bg-white/5 p-6">

            <div className="flex items-center gap-3 mb-4">

              <div className="h-10 w-10 rounded-xl bg-emerald-500/10 flex items-center justify-center">
                <CalendarDays
                  size={19}
                  className="text-emerald-400"
                />
              </div>

              <span className="text-sm text-gray-400">
                Latest campaign
              </span>

            </div>

            <p className="text-lg font-semibold">
              {campaigns.length > 0
                ? formatDate(
                    campaigns[0].created_at
                  )
                : "—"}
            </p>

          </div>

        </div>

        {/* Campaigns */}
        {campaigns.length === 0 ? (

          <motion.div
            initial={{
              opacity: 0,
              y: 10,
            }}
            animate={{
              opacity: 1,
              y: 0,
            }}
            className="rounded-2xl border border-dashed border-white/10 bg-white/[0.02] p-14 text-center"
          >

            <div className="mx-auto h-16 w-16 rounded-2xl bg-indigo-500/10 flex items-center justify-center mb-5">
              <Megaphone
                size={28}
                className="text-indigo-400"
              />
            </div>

            <h3 className="text-xl font-semibold">
              Create your first campaign
            </h3>

            <p className="text-gray-500 max-w-lg mx-auto mt-2 mb-7">
              Create a sales campaign and define at
              least one Ideal Customer Profile.
            </p>

            <button
              onClick={() =>
                router.push(
                  "/dashboard/campaigns/new"
                )
              }
              className="inline-flex items-center gap-2 rounded-xl bg-white text-black px-6 py-3 font-semibold text-sm hover:bg-gray-200 transition-all"
            >
              <Plus size={17} />
              Create campaign
            </button>

          </motion.div>

        ) : (

          <div>

            <div className="flex items-center justify-between mb-5">

              <div>
                <h3 className="text-xl font-semibold">
                  Your campaigns
                </h3>

                <p className="text-sm text-gray-500 mt-1">
                  Select a campaign to manage its ICPs
                  and sales automation.
                </p>
              </div>

            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">

              {campaigns.map(
                (campaign, index) => (

                  <motion.button
                    key={campaign.id}
                    initial={{
                      opacity: 0,
                      y: 15,
                    }}
                    animate={{
                      opacity: 1,
                      y: 0,
                    }}
                    transition={{
                      delay: index * 0.05,
                    }}
                    onClick={() =>
                      router.push(
                        `/dashboard/campaigns/${campaign.id}`
                      )
                    }
                    className="text-left group rounded-2xl border border-white/10 bg-white/5 p-6 hover:bg-white/[0.08] hover:border-indigo-500/30 transition-all"
                  >

                    <div className="flex items-start justify-between mb-5">

                      <div className="h-11 w-11 rounded-xl bg-indigo-500/10 flex items-center justify-center">
                        <Megaphone
                          size={20}
                          className="text-indigo-400"
                        />
                      </div>

                      <ArrowRight
                        size={18}
                        className="text-gray-600 group-hover:text-white group-hover:translate-x-1 transition-all"
                      />

                    </div>

                    {/* Campaign objective */}
                    <h4 className="font-semibold text-lg line-clamp-2">
                      {campaign.objective ||
                        "Sales Campaign"}
                    </h4>

                    {/* Geography */}
                    <div className="flex flex-wrap gap-2 mt-4">

                      {campaign.geography
                        ?.slice(0, 3)
                        .map((geo) => (
                          <span
                            key={geo}
                            className="px-2.5 py-1 rounded-lg bg-white/5 border border-white/10 text-xs text-gray-400"
                          >
                            {geo}
                          </span>
                        ))}

                    </div>

                    {/* Personas */}
                    {campaign.target_personas
                      ?.length > 0 && (
                      <div className="mt-3">

                        <p className="text-xs text-gray-600 mb-2">
                          Target personas
                        </p>

                        <div className="flex flex-wrap gap-2">

                          {campaign.target_personas
                            .slice(0, 3)
                            .map((persona) => (
                              <span
                                key={persona}
                                className="px-2.5 py-1 rounded-lg bg-indigo-500/5 border border-indigo-500/10 text-xs text-indigo-300"
                              >
                                {persona}
                              </span>
                            ))}

                        </div>

                      </div>
                    )}

                    {/* Footer */}
                    <div className="mt-6 pt-4 border-t border-white/10 flex items-center justify-between">

                      <span className="text-xs text-gray-600">
                        Created{" "}
                        {formatDate(
                          campaign.created_at
                        )}
                      </span>

                      <span className="text-xs text-indigo-400">
                        Open campaign
                      </span>

                    </div>

                  </motion.button>

                )
              )}

            </div>

          </div>

        )}

      </div>
    </main>
  );
}