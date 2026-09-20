"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";

import { supabase } from "../../lib/supabase/client";

/**
 * OAuth landing page.
 *
 * The Supabase client is configured with detectSessionInUrl, so it
 * consumes the tokens in the URL on load. We wait for that to finish
 * and then forward the user into the app.
 */
export default function AuthCallback() {
  const router = useRouter();

  useEffect(() => {
    let settled = false;

    const forward = (path: string) => {
      if (settled) return;
      settled = true;
      router.replace(path);
    };

    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) forward("/onboarding");
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session) forward("/onboarding");
    });

    // If no session ever arrives, the sign-in did not complete.
    const timeout = setTimeout(() => forward("/auth"), 8000);

    return () => {
      subscription.unsubscribe();
      clearTimeout(timeout);
    };
  }, [router]);

  return (
    <main className="flex min-h-screen flex-1 items-center justify-center bg-[#070b14] text-white">
      <div className="flex items-center gap-3 text-gray-400">
        <Loader2 size={18} className="animate-spin" />
        Completing sign in...
      </div>
    </main>
  );
}
