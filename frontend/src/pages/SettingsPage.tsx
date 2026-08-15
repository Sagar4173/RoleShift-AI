import { CheckCircle2, Info, Lock, Server, ShieldCheck, XCircle } from "lucide-react";

import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { PageHeader } from "../components/ui/PageHeader";
import { Spinner } from "../components/ui/Spinner";
import { useApi } from "../hooks/useApi";
import { api } from "../services/api";

const CAPABILITIES = [
  {
    title: "Role Intelligence",
    description:
      "Every role can be analyzed through the AI pipeline to produce exposure, automation, augmentation, and future-role profiles — persisted and explainable.",
  },
  {
    title: "Workforce reskilling",
    description:
      "Future skill requirements are aggregated from real analyses into reskilling demand, so workforce planning is grounded in evidence.",
  },
  {
    title: "Explainability",
    description:
      "Every major conclusion surfaces its reasoning and model provenance, so decisions can be audited rather than trusted blindly.",
  },
];

function Connectivity({ label, loading, error }: { label: string; loading: boolean; error: string | null }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <div className="flex items-center gap-2">
        <Server size={14} className="text-ink-muted" aria-hidden="true" />
        <span className="text-sm text-ink-secondary">{label}</span>
      </div>
      {loading ? (
        <Spinner className="h-5" />
      ) : error ? (
        <span className="inline-flex items-center gap-1 text-xs font-medium text-danger-600">
          <XCircle size={13} aria-hidden="true" />
          Unreachable
        </span>
      ) : (
        <span className="inline-flex items-center gap-1 text-xs font-medium text-success-600">
          <CheckCircle2 size={13} aria-hidden="true" />
          Connected
        </span>
      )}
    </div>
  );
}

export function SettingsPage() {
  const connectivity = useApi(() => api.listSkills(0, 1));

  return (
    <div className="animate-fade-up">
      <PageHeader
        eyebrow="Platform"
        title="Settings"
        description="Application information and workspace configuration. This view is read-only."
      />

      <div className="max-w-2xl space-y-6">
        <Card title="Workspace" subtitle="RoleShift AI — Enterprise Intelligence OS.">
          <dl className="space-y-2.5 text-sm">
            <div className="flex items-center justify-between">
              <dt className="text-ink-secondary">Edition</dt>
              <dd className="font-medium text-ink-primary">Enterprise</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-ink-secondary">Data source</dt>
              <dd className="font-medium text-ink-primary">Live API</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-ink-secondary">Analysis engine</dt>
              <dd className="font-medium text-ink-primary">Configured server-side</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-ink-secondary">AI provider</dt>
              <dd className="font-medium text-ink-primary">
                Managed server-side — credentials never exposed
              </dd>
            </div>
          </dl>
        </Card>

        <Card title="API status" subtitle="Live connectivity to the backend.">
          <div className="space-y-3">
            <Connectivity
              label="RoleShift API"
              loading={connectivity.loading}
              error={connectivity.error}
            />
            <p className="flex items-start gap-2 text-xs text-ink-muted">
              <Info size={13} className="mt-0.5 shrink-0" aria-hidden="true" />
              Connectivity is checked against a real endpoint. Individual features show their own
              status on their respective pages.
            </p>
          </div>
        </Card>

        <Card title="Security & privacy" subtitle="How AI analysis is handled.">
          <ul className="space-y-3 text-sm text-ink-secondary">
            <li className="flex items-start gap-2">
              <ShieldCheck size={15} className="mt-0.5 shrink-0 text-brand-600" aria-hidden="true" />
              AI analysis runs entirely on the backend. The browser never holds provider keys,
              prompts, or model configuration.
            </li>
            <li className="flex items-start gap-2">
              <Lock size={15} className="mt-0.5 shrink-0 text-brand-600" aria-hidden="true" />
              Analysis results and their provenance (provider, model, prompt version) are persisted
              and shown inline for auditing.
            </li>
          </ul>
        </Card>

        <Card title="Capabilities" subtitle="What this workspace offers today.">
          <ul className="space-y-4">
            {CAPABILITIES.map((capability) => (
              <li key={capability.title}>
                <p className="text-sm font-semibold text-ink-primary">{capability.title}</p>
                <p className="mt-0.5 text-xs leading-relaxed text-ink-secondary">
                  {capability.description}
                </p>
              </li>
            ))}
          </ul>
        </Card>

        <div>
          <Badge tone="neutral">Read-only view</Badge>
        </div>
      </div>
    </div>
  );
}
