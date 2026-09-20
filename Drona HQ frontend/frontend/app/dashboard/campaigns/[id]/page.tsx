"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { api, type CampaignDetail } from "../../../lib/api";
import { getSession } from "../../../lib/supabase/session";

import CampaignHeader, {
  type CampaignTab,
} from "../../../components/dashboard/campaign/CampaignHeader";
import CampaignOverview from "../../../components/dashboard/campaign/CampaignOverview";
import CampaignCompanies from "../../../components/dashboard/campaign/CampaignCompanies";
import CampaignICPs from "../../../components/dashboard/campaign/CampaignICPs";
import CampaignAgents, {
  type ICPFitmentState,
} from "../../../components/dashboard/campaign/CampaignAgents";
import CampaignProspects from "../../../components/dashboard/campaign/CampaignProspects";
import CampaignKnowledge from "../../../components/dashboard/campaign/CampaignKnowledge";
import CampaignConversations from "../../../components/dashboard/campaign/CampaignConversations";
import CampaignActivity from "../../../components/dashboard/campaign/CampaignActivity";
import { Button, ErrorNote, Spinner } from "../../../components/dashboard/campaign/ui";

export default function CampaignPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();

  const campaignId = params.id;

  const [detail, setDetail] = useState<CampaignDetail | null>(null);
  const [companyName, setCompanyName] = useState("");
  const [tab, setTab] = useState<CampaignTab>("overview");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /* Bumped whenever an agent changes data, so tabs reload. */
  const [refreshToken, setRefreshToken] = useState(0);

  const [fitmentStates, setFitmentStates] = useState<
    Record<string, ICPFitmentState>
  >({});

  /* ============================================================
     LOAD
     ============================================================ */

  const loadCampaign = useCallback(async () => {
    try {
      setError(null);

      const session = await getSession();

      if (!session) {
        router.replace("/auth");
        return;
      }

      const { profile } = await api.getProfile();

      if (!profile.onboarding_completed) {
        router.replace("/onboarding");
        return;
      }

      setCompanyName(profile.company_name || "");

      setDetail(await api.getCampaign(campaignId));
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to load the campaign."
      );
    } finally {
      setLoading(false);
    }
  }, [campaignId, router]);

  useEffect(() => {
    loadCampaign();
  }, [loadCampaign]);

  const refreshAll = useCallback(() => {
    loadCampaign();
    setRefreshToken((token) => token + 1);
  }, [loadCampaign]);

  /* ============================================================
     ICP FITMENT
     ============================================================ */

  const loadFitmentResults = useCallback(async (icpId: string) => {
    try {
      const { metrics, results } = await api.getICPFitmentResults(icpId);

      setFitmentStates((previous) => ({
        ...previous,
        [icpId]: { running: false, metrics, results, error: null },
      }));
    } catch (err) {
      setFitmentStates((previous) => ({
        ...previous,
        [icpId]: {
          running: false,
          metrics: previous[icpId]?.metrics || null,
          results: previous[icpId]?.results || [],
          error:
            err instanceof Error
              ? err.message
              : "Unable to load ICP fitment results.",
        },
      }));
    }
  }, []);

  useEffect(() => {
    detail?.icps.forEach((icp) => loadFitmentResults(icp.id));
  }, [detail?.icps, loadFitmentResults, refreshToken]);

  const runFitment = async (icpId: string) => {
    if (!detail) return;

    /* The agent has nothing to score without target companies. */
    if (detail.company_ids.length === 0) {
      setFitmentStates((previous) => ({
        ...previous,
        [icpId]: {
          running: false,
          metrics: previous[icpId]?.metrics || null,
          results: previous[icpId]?.results || [],
          error:
            "Select at least one target company before running ICP fitment.",
        },
      }));

      return;
    }

    setFitmentStates((previous) => ({
      ...previous,
      [icpId]: {
        running: true,
        metrics: previous[icpId]?.metrics || null,
        results: previous[icpId]?.results || [],
        error: null,
      },
    }));

    try {
      await api.runICPFitment(icpId, detail.company_ids);

      await loadFitmentResults(icpId);

      refreshAll();
    } catch (err) {
      setFitmentStates((previous) => ({
        ...previous,
        [icpId]: {
          running: false,
          metrics: previous[icpId]?.metrics || null,
          results: previous[icpId]?.results || [],
          error:
            err instanceof Error
              ? err.message
              : "The ICP fitment agent failed.",
        },
      }));
    }
  };

  /* ============================================================
     RENDER
     ============================================================ */

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#070b14]">
        <Spinner label="Loading campaign..." />
      </main>
    );
  }

  if (error || !detail) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#070b14] px-6">
        <div className="w-full max-w-md space-y-4 text-center">
          <ErrorNote message={error || "Campaign not found."} />

          <Button onClick={() => router.push("/dashboard")}>
            Back to campaigns
          </Button>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#070b14] text-white">
      <div className="mx-auto max-w-7xl px-6 py-8">
        <CampaignHeader
          campaign={detail.campaign}
          companyName={companyName}
          activeTab={tab}
          onTabChange={setTab}
        />

        {tab === "overview" && (
          <CampaignOverview
            campaign={detail.campaign}
            stats={detail.stats}
          />
        )}

        {tab === "companies" && (
          <CampaignCompanies
            campaignId={campaignId}
            companies={detail.companies}
            selectedCompanyIds={detail.company_ids}
            onSaved={refreshAll}
          />
        )}

        {tab === "icps" && (
          <CampaignICPs campaignId={campaignId} icps={detail.icps} />
        )}

        {tab === "prospects" && (
          <CampaignProspects
            campaignId={campaignId}
            refreshToken={refreshToken}
            onChanged={refreshAll}
          />
        )}

        {tab === "agents" && (
          <CampaignAgents
            campaignId={campaignId}
            icps={detail.icps}
            agents={detail.agents}
            fitmentStates={fitmentStates}
            onRunFitment={runFitment}
            onRefreshFitment={loadFitmentResults}
            onPipelineComplete={refreshAll}
          />
        )}

        {tab === "knowledge" && (
          <CampaignKnowledge
            campaignId={campaignId}
            onChanged={refreshAll}
          />
        )}

        {tab === "conversations" && (
          <CampaignConversations
            campaignId={campaignId}
            refreshToken={refreshToken}
            onChanged={refreshAll}
          />
        )}

        {tab === "activity" && (
          <CampaignActivity
            campaignId={campaignId}
            refreshToken={refreshToken}
          />
        )}
      </div>
    </main>
  );
}
