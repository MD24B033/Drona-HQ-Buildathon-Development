"use client";

import { ReactNode } from "react";
import { Loader2 } from "lucide-react";

/* ============================================================
   PANEL
   ============================================================ */

export function Panel({
  title,
  description,
  action,
  children,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-white/10 bg-white/5 p-6">
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">{title}</h2>

          {description && (
            <p className="mt-1 text-sm text-gray-400">{description}</p>
          )}
        </div>

        {action && <div className="shrink-0">{action}</div>}
      </div>

      {children}
    </section>
  );
}

/* ============================================================
   BUTTONS
   ============================================================ */

type ButtonProps = {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  loading?: boolean;
  variant?: "primary" | "secondary" | "danger";
  size?: "sm" | "md";
  title?: string;
  type?: "button" | "submit";
};

export function Button({
  children,
  onClick,
  disabled,
  loading,
  variant = "secondary",
  size = "md",
  title,
  type = "button",
}: ButtonProps) {
  const variants = {
    primary:
      "bg-gradient-to-r from-indigo-500 to-cyan-500 text-white hover:opacity-90",
    secondary:
      "border border-white/10 bg-white/5 text-gray-200 hover:bg-white/10",
    danger:
      "border border-red-500/30 bg-red-500/10 text-red-300 hover:bg-red-500/20",
  };

  const sizes = {
    sm: "h-9 px-3 text-sm",
    md: "h-11 px-5 text-sm",
  };

  return (
    <button
      type={type}
      title={title}
      onClick={onClick}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center gap-2 rounded-xl font-medium transition-all disabled:cursor-not-allowed disabled:opacity-50 ${variants[variant]} ${sizes[size]}`}
    >
      {loading && <Loader2 size={15} className="animate-spin" />}
      {children}
    </button>
  );
}

/* ============================================================
   FORM FIELDS
   ============================================================ */

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <div>
      <label className="mb-2 block text-sm font-medium text-gray-200">
        {label}
      </label>

      {children}

      {hint && <p className="mt-2 text-xs text-gray-500">{hint}</p>}
    </div>
  );
}

const inputClass =
  "w-full rounded-xl border border-white/10 bg-white/5 px-4 text-white outline-none transition-all placeholder:text-gray-600 focus:border-indigo-500";

export function TextInput({
  value,
  onChange,
  placeholder,
  type = "text",
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  type?: string;
}) {
  return (
    <input
      type={type}
      value={value}
      placeholder={placeholder}
      onChange={(event) => onChange(event.target.value)}
      className={`${inputClass} h-12`}
    />
  );
}

export function TextArea({
  value,
  onChange,
  placeholder,
  rows = 4,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  rows?: number;
}) {
  return (
    <textarea
      rows={rows}
      value={value}
      placeholder={placeholder}
      onChange={(event) => onChange(event.target.value)}
      className={`${inputClass} resize-none py-3`}
    />
  );
}

/* ============================================================
   STATUS
   ============================================================ */

const BADGE_STYLES: Record<string, string> = {
  qualified: "bg-emerald-500/10 text-emerald-300 border-emerald-500/20",
  disqualified: "bg-red-500/10 text-red-300 border-red-500/20",
  needs_review: "bg-amber-500/10 text-amber-300 border-amber-500/20",
  completed: "bg-emerald-500/10 text-emerald-300 border-emerald-500/20",
  running: "bg-indigo-500/10 text-indigo-300 border-indigo-500/20",
  failed: "bg-red-500/10 text-red-300 border-red-500/20",
  active: "bg-emerald-500/10 text-emerald-300 border-emerald-500/20",
  paused: "bg-amber-500/10 text-amber-300 border-amber-500/20",
  escalated: "bg-orange-500/10 text-orange-300 border-orange-500/20",
  closed: "bg-gray-500/10 text-gray-400 border-white/10",
  stopped: "bg-gray-500/10 text-gray-400 border-white/10",
  positive: "bg-emerald-500/10 text-emerald-300 border-emerald-500/20",
  negative: "bg-red-500/10 text-red-300 border-red-500/20",
  neutral: "bg-white/5 text-gray-300 border-white/10",
};

export function Badge({ value }: { value: string | null | undefined }) {
  if (!value) return null;

  const style =
    BADGE_STYLES[value] || "bg-white/5 text-gray-300 border-white/10";

  return (
    <span
      className={`inline-block whitespace-nowrap rounded-full border px-2.5 py-1 text-xs font-medium ${style}`}
    >
      {value.replace(/_/g, " ")}
    </span>
  );
}

export function Metric({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: number | string;
  tone?: "default" | "good" | "bad" | "warn";
}) {
  const tones = {
    default: "text-white",
    good: "text-emerald-400",
    bad: "text-red-400",
    warn: "text-amber-400",
  };

  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
      <p className="text-xs text-gray-500">{label}</p>

      <p className={`mt-1 text-2xl font-semibold ${tones[tone]}`}>
        {value}
      </p>
    </div>
  );
}

/* ============================================================
   FEEDBACK
   ============================================================ */

export function ErrorNote({ message }: { message: string | null }) {
  if (!message) return null;

  return (
    <div className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
      {message}
    </div>
  );
}

export function SuccessNote({ message }: { message: string | null }) {
  if (!message) return null;

  return (
    <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">
      {message}
    </div>
  );
}

export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon: ReactNode;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.02] p-12 text-center">
      <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-500/10 text-indigo-400">
        {icon}
      </div>

      <h3 className="font-semibold text-white">{title}</h3>

      <p className="mx-auto mt-1 max-w-md text-sm text-gray-500">
        {description}
      </p>

      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function Spinner({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-12 text-gray-400">
      <Loader2 size={18} className="animate-spin" />
      {label}
    </div>
  );
}

/* ============================================================
   HELPERS
   ============================================================ */

export function formatDate(value: string | null | undefined) {
  if (!value) return "—";

  return new Date(value).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function agentLabel(agentType: string) {
  return agentType
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
