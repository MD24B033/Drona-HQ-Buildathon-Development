"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";

/**
 * The campaign list lives on the dashboard itself; several screens link
 * to /dashboard/campaigns, so this route forwards there.
 */
export default function CampaignsIndex() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/dashboard");
  }, [router]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#070b14] text-white">
      <div className="flex items-center gap-3 text-gray-400">
        <Loader2 size={18} className="animate-spin" />
        Loading campaigns...
      </div>
    </main>
  );
}
