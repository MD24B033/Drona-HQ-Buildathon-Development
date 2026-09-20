"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { api } from "../../lib/api";
import { getSession } from "../../lib/supabase/session";

export default function OnboardingPage() {
  const router = useRouter();

  /*
   * The dashboard links here with ?edit=1 for "Company settings",
   * which keeps the form open instead of bouncing to the dashboard.
   *
   * The flag is read from the URL directly rather than with
   * useSearchParams, so this page needs no Suspense boundary.
   */
  const [editing, setEditing] = useState(false);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const [form, setForm] = useState({
    company_name: "",
    company_website: "",
    employee_count: "",
    industry: "",
    business_model: "",
    company_description: "",
  });

  useEffect(() => {
    const loadProfile = async () => {
      const session = await getSession();

      if (!session) {
        router.replace("/auth");
        return;
      }

      const isEditing =
        new URLSearchParams(window.location.search).get("edit") === "1";

      setEditing(isEditing);

      try {
        const { profile } = await api.getProfile();

        if (profile.onboarding_completed && !isEditing) {
          router.replace("/dashboard");
          return;
        }

        // Keep any partially completed information.
        setForm({
          company_name: profile.company_name || "",
          company_website: profile.company_website || "",
          employee_count: profile.employee_count?.toString() || "",
          industry: profile.industry || "",
          business_model: profile.business_model || "",
          company_description: profile.company_description || "",
        });
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load your profile."
        );
      } finally {
        setLoading(false);
      }
    };

    loadProfile();
  }, [router]);

  const updateField = (
    field: keyof typeof form,
    value: string
  ) => {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
  };

  const handleSubmit = async (
    e: React.FormEvent<HTMLFormElement>
  ) => {
    e.preventDefault();

    setError("");
    setSaving(true);

    try {
      await api.updateProfile({
        company_name: form.company_name.trim(),
        company_website: form.company_website.trim(),
        employee_count: Number(form.employee_count) || null,
        industry: form.industry,
        business_model: form.business_model,
        company_description: form.company_description.trim(),
        onboarding_completed: true,
      });

      router.replace("/dashboard");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to save your company profile."
      );

      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#070b14] flex items-center justify-center text-white">
        <div className="text-gray-400 animate-pulse">
          Loading...
        </div>
      </div>
    );
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#070b14] px-4 py-12 text-white">

      {/* Background Glow */}
      <div className="absolute top-[-160px] left-[-160px] w-[450px] h-[450px] bg-indigo-500/20 rounded-full blur-3xl" />

      <div className="absolute bottom-[-180px] right-[-180px] w-[450px] h-[450px] bg-cyan-500/10 rounded-full blur-3xl" />

      <div className="relative z-10 mx-auto max-w-2xl">

        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8 text-center"
        >
          <p className="text-sm font-medium text-indigo-400 mb-3">
            {editing ? "Company settings" : "One-time setup"}
          </p>

          <h1 className="text-4xl font-bold tracking-tight">
            Tell us about your company
          </h1>

          <p className="mt-3 text-gray-400 max-w-xl mx-auto">
            This information helps us configure your sales
            automation and personalize your prospecting
            workflows.
          </p>
        </motion.div>

        {/* Form Card */}
        <motion.div
          initial={{ opacity: 0, y: 25 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="rounded-[28px] border border-white/10 bg-white/5 backdrop-blur-2xl p-7 md:p-9 shadow-[0_0_80px_rgba(99,102,241,0.10)]"
        >

          <form
            onSubmit={handleSubmit}
            className="space-y-6"
          >

            {/* Company Name */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Company name
              </label>

              <input
                required
                type="text"
                value={form.company_name}
                onChange={(e) =>
                  updateField(
                    "company_name",
                    e.target.value
                  )
                }
                placeholder="Acme Inc."
                className="w-full h-14 rounded-2xl bg-white/5 border border-white/10 px-5 outline-none focus:border-indigo-500 transition-all text-white placeholder:text-gray-600"
              />
            </div>

            {/* Website */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Company website
              </label>

              <input
                required
                type="url"
                value={form.company_website}
                onChange={(e) =>
                  updateField(
                    "company_website",
                    e.target.value
                  )
                }
                placeholder="https://yourcompany.com"
                className="w-full h-14 rounded-2xl bg-white/5 border border-white/10 px-5 outline-none focus:border-indigo-500 transition-all text-white placeholder:text-gray-600"
              />
            </div>

            {/* Employee Count */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Company size
              </label>

              <select
                required
                value={form.employee_count}
                onChange={(e) =>
                  updateField(
                    "employee_count",
                    e.target.value
                  )
                }
                className="w-full h-14 rounded-2xl bg-white/5 border border-white/10 px-5 outline-none focus:border-indigo-500 transition-all text-white"
              >
                <option
                  value=""
                  className="bg-[#111827]"
                >
                  Select company size
                </option>

                <option
                  value="5"
                  className="bg-[#111827]"
                >
                  1–10 employees
                </option>

                <option
                  value="25"
                  className="bg-[#111827]"
                >
                  11–50 employees
                </option>

                <option
                  value="100"
                  className="bg-[#111827]"
                >
                  51–200 employees
                </option>

                <option
                  value="350"
                  className="bg-[#111827]"
                >
                  201–500 employees
                </option>

                <option
                  value="750"
                  className="bg-[#111827]"
                >
                  501–1,000 employees
                </option>

                <option
                  value="2500"
                  className="bg-[#111827]"
                >
                  1,001–5,000 employees
                </option>

                <option
                  value="5001"
                  className="bg-[#111827]"
                >
                  5,000+ employees
                </option>
              </select>
            </div>

            {/* Industry */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Industry
              </label>

              <select
                required
                value={form.industry}
                onChange={(e) =>
                  updateField(
                    "industry",
                    e.target.value
                  )
                }
                className="w-full h-14 rounded-2xl bg-white/5 border border-white/10 px-5 outline-none focus:border-indigo-500 transition-all text-white"
              >
                <option
                  value=""
                  className="bg-[#111827]"
                >
                  Select your industry
                </option>

                <option
                  value="SaaS"
                  className="bg-[#111827]"
                >
                  SaaS
                </option>

                <option
                  value="Technology"
                  className="bg-[#111827]"
                >
                  Technology
                </option>

                <option
                  value="FinTech"
                  className="bg-[#111827]"
                >
                  FinTech
                </option>

                <option
                  value="HealthTech"
                  className="bg-[#111827]"
                >
                  HealthTech
                </option>

                <option
                  value="E-commerce"
                  className="bg-[#111827]"
                >
                  E-commerce
                </option>

                <option
                  value="Marketing"
                  className="bg-[#111827]"
                >
                  Marketing
                </option>

                <option
                  value="Consulting"
                  className="bg-[#111827]"
                >
                  Consulting
                </option>

                <option
                  value="Financial Services"
                  className="bg-[#111827]"
                >
                  Financial Services
                </option>

                <option
                  value="Real Estate"
                  className="bg-[#111827]"
                >
                  Real Estate
                </option>

                <option
                  value="Manufacturing"
                  className="bg-[#111827]"
                >
                  Manufacturing
                </option>

                <option
                  value="Education"
                  className="bg-[#111827]"
                >
                  Education
                </option>

                <option
                  value="Other"
                  className="bg-[#111827]"
                >
                  Other
                </option>
              </select>
            </div>

            {/* Business Model */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Business model
              </label>

              <select
                required
                value={form.business_model}
                onChange={(e) =>
                  updateField(
                    "business_model",
                    e.target.value
                  )
                }
                className="w-full h-14 rounded-2xl bg-white/5 border border-white/10 px-5 outline-none focus:border-indigo-500 transition-all text-white"
              >
                <option
                  value=""
                  className="bg-[#111827]"
                >
                  Select business model
                </option>

                <option
                  value="B2B"
                  className="bg-[#111827]"
                >
                  B2B
                </option>

                <option
                  value="B2C"
                  className="bg-[#111827]"
                >
                  B2C
                </option>

                <option
                  value="B2B2C"
                  className="bg-[#111827]"
                >
                  B2B2C
                </option>

                <option
                  value="D2C"
                  className="bg-[#111827]"
                >
                  D2C
                </option>

                <option
                  value="Marketplace"
                  className="bg-[#111827]"
                >
                  Marketplace
                </option>

                <option
                  value="Agency"
                  className="bg-[#111827]"
                >
                  Agency / Services
                </option>

                <option
                  value="Other"
                  className="bg-[#111827]"
                >
                  Other
                </option>
              </select>
            </div>

            {/* Company Description */}
            <div>
              <label className="block text-sm font-medium mb-2">
                What does your company do?
              </label>

              <textarea
                required
                rows={5}
                value={form.company_description}
                onChange={(e) =>
                  updateField(
                    "company_description",
                    e.target.value
                  )
                }
                placeholder="Describe your products or services, who you sell to, and the problems your company solves..."
                className="w-full rounded-2xl bg-white/5 border border-white/10 px-5 py-4 outline-none focus:border-indigo-500 transition-all text-white placeholder:text-gray-600 resize-none"
              />
            </div>

            {/* Error */}
            {error && (
              <div className="rounded-2xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
                {error}
              </div>
            )}

            {/* Submit */}
            <motion.button
              type="submit"
              whileTap={{ scale: 0.98 }}
              disabled={saving}
              className="w-full h-14 rounded-2xl bg-gradient-to-r from-indigo-500 to-cyan-500 font-semibold text-white shadow-lg shadow-indigo-500/20 hover:opacity-90 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving
                ? "Saving your company profile..."
                : editing
                  ? "Save changes"
                  : "Complete setup"}
            </motion.button>

          </form>
        </motion.div>

        <p className="text-center text-xs text-gray-600 mt-6">
          You can update these details later from your
          account settings.
        </p>
      </div>
    </main>
  );
}

