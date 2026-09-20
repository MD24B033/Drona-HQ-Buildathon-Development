"use client";

import { useEffect, useState } from "react";
import { Building2, Check, Plus, Search, X } from "lucide-react";

import { api, type Company } from "../../../lib/api";
import {
  Button,
  ErrorNote,
  Field,
  Panel,
  SuccessNote,
  TextInput,
} from "./ui";

export default function CampaignCompanies({
  campaignId,
  companies,
  selectedCompanyIds,
  onSaved,
}: {
  campaignId: string;
  companies: Company[];
  selectedCompanyIds: string[];
  onSaved: () => void;
}) {
  const [allCompanies, setAllCompanies] = useState<Company[]>(companies);
  const [selected, setSelected] = useState<string[]>(selectedCompanyIds);
  const [search, setSearch] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);

  const [adding, setAdding] = useState(false);
  const [newCompany, setNewCompany] = useState({
    name: "",
    website: "",
    industry: "",
  });

  /* The full company pool is wider than this campaign's selection. */
  useEffect(() => {
    api
      .listCompanies()
      .then(({ companies }) => setAllCompanies(companies))
      .catch(() => setAllCompanies(companies));
  }, [companies]);

  useEffect(() => {
    setSelected(selectedCompanyIds);
  }, [selectedCompanyIds]);

  const query = search.toLowerCase();

  const filtered = allCompanies.filter(
    (company) =>
      company.name?.toLowerCase().includes(query) ||
      company.industry?.toLowerCase().includes(query) ||
      company.website?.toLowerCase().includes(query)
  );

  const toggle = (companyId: string) => {
    setSaved(null);

    setSelected((current) =>
      current.includes(companyId)
        ? current.filter((id) => id !== companyId)
        : [...current, companyId]
    );
  };

  const save = async () => {
    setSaving(true);
    setError(null);
    setSaved(null);

    try {
      await api.setCampaignCompanies(campaignId, selected);

      setSaved(
        `${selected.length} ${
          selected.length === 1 ? "company" : "companies"
        } targeted by this campaign.`
      );

      onSaved();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to save companies."
      );
    } finally {
      setSaving(false);
    }
  };

  const addCompany = async () => {
    if (!newCompany.name.trim()) {
      setError("A company needs a name.");
      return;
    }

    setError(null);

    try {
      const { company } = await api.createCompany({
        name: newCompany.name.trim(),
        website: newCompany.website.trim() || null,
        industry: newCompany.industry.trim() || null,
      });

      setAllCompanies((current) => [company, ...current]);
      setSelected((current) => [...current, company.id]);
      setNewCompany({ name: "", website: "", industry: "" });
      setAdding(false);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to add the company."
      );
    }
  };

  return (
    <Panel
      title="Target companies"
      description="The agents only look for prospects inside the companies selected here."
      action={
        <div className="flex items-center gap-3">
          <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-medium text-gray-300">
            {selected.length} selected
          </span>

          <Button size="sm" onClick={() => setAdding((open) => !open)}>
            <Plus size={15} />
            New company
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        {adding && (
          <div className="grid gap-4 rounded-xl border border-white/10 bg-white/[0.03] p-4 sm:grid-cols-3">
            <Field label="Name">
              <TextInput
                value={newCompany.name}
                onChange={(value) =>
                  setNewCompany((current) => ({ ...current, name: value }))
                }
                placeholder="Acme Technologies"
              />
            </Field>

            <Field label="Website">
              <TextInput
                value={newCompany.website}
                onChange={(value) =>
                  setNewCompany((current) => ({
                    ...current,
                    website: value,
                  }))
                }
                placeholder="https://acme.com"
              />
            </Field>

            <Field label="Industry">
              <TextInput
                value={newCompany.industry}
                onChange={(value) =>
                  setNewCompany((current) => ({
                    ...current,
                    industry: value,
                  }))
                }
                placeholder="SaaS"
              />
            </Field>

            <div className="sm:col-span-3">
              <Button variant="primary" size="sm" onClick={addCompany}>
                Add company
              </Button>
            </div>
          </div>
        )}

        <ErrorNote message={error} />
        <SuccessNote message={saved} />

        <div className="relative">
          <Search
            size={16}
            className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-500"
          />

          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search companies..."
            className="h-11 w-full rounded-xl border border-white/10 bg-white/5 pl-10 pr-4 text-sm text-white outline-none transition-all placeholder:text-gray-600 focus:border-indigo-500"
          />
        </div>

        {filtered.length === 0 ? (
          <p className="py-8 text-center text-sm text-gray-500">
            No companies found.
          </p>
        ) : (
          <div className="max-h-96 space-y-2 overflow-y-auto pr-1">
            {filtered.map((company) => {
              const isSelected = selected.includes(company.id);

              return (
                <button
                  key={company.id}
                  type="button"
                  onClick={() => toggle(company.id)}
                  className={`flex w-full items-center justify-between rounded-xl border p-3 text-left transition ${
                    isSelected
                      ? "border-indigo-500/40 bg-indigo-500/10"
                      : "border-white/10 bg-white/[0.02] hover:bg-white/5"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-white/5">
                      <Building2 size={16} className="text-gray-400" />
                    </div>

                    <div>
                      <p className="text-sm font-medium text-white">
                        {company.name}
                      </p>

                      <p className="text-xs text-gray-500">
                        {[company.industry, company.website]
                          .filter(Boolean)
                          .join(" · ") || "No details"}
                      </p>
                    </div>
                  </div>

                  <div
                    className={`flex h-5 w-5 items-center justify-center rounded border ${
                      isSelected
                        ? "border-indigo-500 bg-indigo-500 text-white"
                        : "border-white/20"
                    }`}
                  >
                    {isSelected && <Check size={13} />}
                  </div>
                </button>
              );
            })}
          </div>
        )}

        {selected.length > 0 && (
          <div className="border-t border-white/10 pt-4">
            <p className="mb-2 text-xs uppercase tracking-wide text-gray-500">
              Selected
            </p>

            <div className="flex flex-wrap gap-2">
              {selected.map((companyId) => {
                const company = allCompanies.find(
                  (item) => item.id === companyId
                );

                if (!company) return null;

                return (
                  <span
                    key={company.id}
                    className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-gray-300"
                  >
                    {company.name}

                    <button
                      type="button"
                      onClick={() => toggle(company.id)}
                      className="text-gray-500 transition hover:text-white"
                    >
                      <X size={12} />
                    </button>
                  </span>
                );
              })}
            </div>
          </div>
        )}

        <div className="flex justify-end border-t border-white/10 pt-4">
          <Button variant="primary" onClick={save} loading={saving}>
            Save companies
          </Button>
        </div>
      </div>
    </Panel>
  );
}
