"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";

import { api } from "../../../../../lib/api";
import ICPForm, {
  type ICPFormValues,
} from "../../../../../components/dashboard/campaign/ICPForm";

export default function NewICPPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();

  const campaignId = params.id;

  const create = async (values: ICPFormValues) => {
    const { icp } = await api.createICP(campaignId, values);

    router.replace(`/dashboard/campaigns/${campaignId}/icps/${icp.id}`);
  };

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

        <h1 className="mb-8 text-3xl font-bold">New ICP</h1>

        <ICPForm submitLabel="Create ICP" onSubmit={create} />
      </div>
    </main>
  );
}
