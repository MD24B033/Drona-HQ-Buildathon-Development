"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";

import { getSession } from "./lib/supabase/session";

/**
 * Entry point: send the visitor wherever they belong.
 */
export default function Home() {
  const router = useRouter();

  useEffect(() => {
    const route = async () => {
      const session = await getSession();

      router.replace(session ? "/dashboard" : "/auth");
    };

    route();
  }, [router]);

  return (
    <main className="flex min-h-screen flex-1 items-center justify-center bg-[#070b14] text-white">
      <div className="flex items-center gap-3 text-gray-400">
        <Loader2 size={18} className="animate-spin" />
        Loading...
      </div>
    </main>
  );
}
