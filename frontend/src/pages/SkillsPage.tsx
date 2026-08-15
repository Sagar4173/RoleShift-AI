import { BookOpen, TrendingUp, Users } from "lucide-react";
import { Link } from "react-router-dom";

import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { PageHeader } from "../components/ui/PageHeader";
import { PriorityBadge } from "../components/ui/PriorityBadge";
import { ScoreBar } from "../components/ui/Metrics";
import { Skeleton } from "../components/ui/Skeleton";
import { useApi } from "../hooks/useApi";
import { formatPercent } from "../lib/utils";
import { api } from "../services/api";

export function SkillsPage() {
  const demand = useApi(() => api.getSkillsSummary());
  const catalogue = useApi(() => api.listSkills(0, 200));

  return (
    <div className="animate-fade-up">
      <PageHeader
        eyebrow="Workforce planning"
        title="Skills & Reskilling"
        description="Emerging skill demand derived from real role analyses, alongside your organisation's skill catalogue."
      />

      <Card
        title="Top emerging skills"
        subtitle="Future skill requirements aggregated across all analyzed roles, ranked by average relevance."
      >
        {demand.loading ? (
          <div className="space-y-3">
            <Skeleton className="h-14" />
            <Skeleton className="h-14" />
            <Skeleton className="h-14" />
          </div>
        ) : demand.error ? (
          <ErrorState title="Could not load reskilling demand" description={demand.error} onRetry={demand.refetch} />
        ) : demand.data && demand.data.items.length > 0 ? (
          <ol className="space-y-4">
            {demand.data.items.map((item, index) => (
              <li key={item.name} className="rounded-xl border border-border-default bg-surface-sunken p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex min-w-0 items-start gap-3">
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-surface-card text-[11px] font-semibold tabular-nums text-ink-muted shadow-card">
                      {index + 1}
                    </span>
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm font-semibold text-ink-primary">{item.name}</p>
                        <PriorityBadge priority={item.priority} />
                        <Badge tone="info">{item.roles.length} role(s)</Badge>
                      </div>
                      {item.category && (
                        <p className="mt-0.5 text-xs text-ink-muted">{item.category}</p>
                      )}
                    </div>
                  </div>
                  <span className="shrink-0 text-sm font-semibold tabular-nums text-ink-primary">
                    {formatPercent(item.relevance)}
                  </span>
                </div>
                <div className="mt-3">
                  <ScoreBar label="" value={item.relevance} accent />
                </div>
                {item.roles.length > 0 && (
                  <div className="mt-3 flex flex-wrap items-center gap-1.5">
                    <span className="flex items-center gap-1 text-[11px] font-medium text-ink-muted">
                      <Users size={12} aria-hidden="true" />
                      Affected roles:
                    </span>
                    {item.roles.map((role) => (
                      <Link
                        key={role.role_id}
                        to={`/role-intelligence/${role.role_id}`}
                        className="chip transition-colors hover:border-brand-200 hover:bg-brand-50 hover:text-brand-700"
                      >
                        {role.role_name}
                      </Link>
                    ))}
                  </div>
                )}
              </li>
            ))}
          </ol>
        ) : (
          <EmptyState
            icon={<TrendingUp size={26} />}
            title="No reskilling demand yet"
            description="Reskilling demand is computed from real role analyses. Once roles are analyzed, their future skill requirements appear here."
          />
        )}
      </Card>

      <div className="mt-6">
        <Card
          title="Skill catalogue"
          subtitle="The persisted skills recorded in your workspace."
        >
          {catalogue.loading ? (
            <div className="space-y-3">
              <Skeleton className="h-10" />
              <Skeleton className="h-10" />
            </div>
          ) : catalogue.error ? (
            <ErrorState title="Could not load the skill catalogue" description={catalogue.error} onRetry={catalogue.refetch} />
          ) : catalogue.data && catalogue.data.items.length > 0 ? (
            <ul className="divide-y divide-border-faint">
              {catalogue.data.items.map((skill) => (
                <li key={skill.id} className="flex items-center justify-between gap-3 py-2.5">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-ink-primary">{skill.name}</p>
                    {skill.description && (
                      <p className="truncate text-xs text-ink-muted">{skill.description}</p>
                    )}
                  </div>
                  {skill.category && (
                    <Badge tone="neutral" className="shrink-0">
                      {skill.category}
                    </Badge>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState
              icon={<BookOpen size={26} />}
              title="No skills in the catalogue yet"
              description="Skills are added to the catalogue by the team as part of workforce data. This view reflects the persisted catalogue only — it contains no fabricated entries."
            />
          )}
        </Card>
      </div>
    </div>
  );
}
