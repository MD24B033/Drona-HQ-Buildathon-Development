"use client";

import { useState } from "react";
import { Target } from "lucide-react";

import type { ICP } from "../../../lib/api";
import {
  Button,
  ErrorNote,
  Field,
  Panel,
  SuccessNote,
  TextArea,
  TextInput,
} from "./ui";

export interface ICPFormValues {
  name: string;
  description: string;
  criteria: Record<string, unknown>;

  /* Lets these values be passed straight to the API's JSON body type. */
  [key: string]: unknown;
}

const toList = (value: string) =>
  value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);

const fromList = (value: unknown) =>
  Array.isArray(value) ? value.map(String).join(", ") : "";

/**
 * Shared create/edit form for an ICP.
 *
 * Criteria are stored as free-form jsonb, so the form keeps the common
 * keys as comma-separated lists plus a free-text catch-all.
 */
export default function ICPForm({
  icp,
  submitLabel,
  onSubmit,
  onDelete,
  notice,
}: {
  icp?: ICP;
  submitLabel: string;
  onSubmit: (values: ICPFormValues) => Promise<void>;
  onDelete?: () => Promise<void>;
  notice?: string | null;
}) {
  const criteria = (icp?.criteria || {}) as Record<string, unknown>;

  const [form, setForm] = useState({
    name: icp?.name || "",
    description: icp?.description || "",
    industries: fromList(criteria.industries),
    company_sizes: fromList(criteria.company_sizes),
    job_titles: fromList(criteria.job_titles),
    technologies: fromList(criteria.technologies),
    other: typeof criteria.other === "string" ? criteria.other : "",
  });

  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const update = (field: keyof typeof form, value: string) =>
    setForm((current) => ({ ...current, [field]: value }));

  const submit = async () => {
    if (!form.name.trim()) {
      setError("Give this ICP a name.");
      return;
    }

    if (!form.description.trim()) {
      setError("Describe the ideal customer.");
      return;
    }

    setSaving(true);
    setError(null);

    try {
      await onSubmit({
        name: form.name.trim(),
        description: form.description.trim(),
        criteria: {
          industries: toList(form.industries),
          company_sizes: toList(form.company_sizes),
          job_titles: toList(form.job_titles),
          technologies: toList(form.technologies),
          other: form.other.trim(),
        },
      });
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to save the ICP."
      );
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    if (!onDelete) return;

    setDeleting(true);
    setError(null);

    try {
      await onDelete();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to delete the ICP."
      );

      setDeleting(false);
    }
  };

  return (
    <div className="space-y-6">
      <Panel
        title="Ideal customer profile"
        description="The fitment agent scores every prospect against exactly these criteria, so be specific."
      >
        <div className="space-y-5">
          <Field label="ICP name">
            <TextInput
              value={form.name}
              onChange={(value) => update("name", value)}
              placeholder="B2B SaaS companies"
            />
          </Field>

          <Field label="Description">
            <TextArea
              value={form.description}
              onChange={(value) => update("description", value)}
              placeholder="The type of company and person that is an ideal customer..."
            />
          </Field>

          <div className="grid gap-5 sm:grid-cols-2">
            <Field label="Industries" hint="Comma separated.">
              <TextInput
                value={form.industries}
                onChange={(value) => update("industries", value)}
                placeholder="SaaS, FinTech"
              />
            </Field>

            <Field label="Company sizes" hint="Comma separated.">
              <TextInput
                value={form.company_sizes}
                onChange={(value) => update("company_sizes", value)}
                placeholder="51-200, 201-500"
              />
            </Field>

            <Field label="Target job titles" hint="Comma separated.">
              <TextInput
                value={form.job_titles}
                onChange={(value) => update("job_titles", value)}
                placeholder="CEO, VP Sales, CRO"
              />
            </Field>

            <Field label="Technologies" hint="Comma separated.">
              <TextInput
                value={form.technologies}
                onChange={(value) => update("technologies", value)}
                placeholder="Salesforce, HubSpot"
              />
            </Field>
          </div>

          <Field label="Additional criteria">
            <TextArea
              value={form.other}
              onChange={(value) => update("other", value)}
              placeholder="Anything else that defines this ICP..."
            />
          </Field>

          <ErrorNote message={error} />
          <SuccessNote message={notice || null} />

          <div className="flex justify-end">
            <Button variant="primary" onClick={submit} loading={saving}>
              <Target size={16} />
              {submitLabel}
            </Button>
          </div>
        </div>
      </Panel>

      {onDelete && (
        <Panel
          title="Delete this ICP"
          description="Its prospect scores are removed with it. A campaign must keep at least one ICP."
        >
          {confirmingDelete ? (
            <div className="flex flex-wrap items-center gap-3">
              <p className="text-sm text-red-300">
                This cannot be undone. Delete it?
              </p>

              <Button variant="danger" onClick={remove} loading={deleting}>
                Yes, delete
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
              Delete ICP
            </Button>
          )}
        </Panel>
      )}
    </div>
  );
}
