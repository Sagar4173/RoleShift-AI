import { ArrowRightLeft, Briefcase, TrendingUp } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { ImpactBadge } from "../components/ui/ImpactBadge";
import { PriorityBadge } from "../components/ui/PriorityBadge";
import { ScoreBar } from "../components/ui/Metrics";
import { Skeleton, SkeletonRow } from "../components/ui/Skeleton";
import { PageHeader } from "../components/ui/PageHeader";
import { useApi } from "../hooks/useApi";
import { formatPercent } from "../lib/utils";
import { api } from "../services/api";
import type { RoleCompareItem, RoleListItem } from "../types/api";

function RoleSelector({
  label,
  value,
  roles,
  onChange,
}: {
  label: string;
  value: string;
  roles: RoleListItem[];
  onChange: (id: string) => void;
}) {
  const analyzed = roles.filter((role) => role.has_analysis);
  const notAnalyzed = roles.filter((role) => !role.has_analysis);

  return (
    <div>
      <label htmlFor={`compare-${label}`} className="label">
        {label}
      </label>
      <select
        id={`compare-${label}`}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="select"
      >
        <option value="">Select a role…</option>
        {analyzed.length > 0 && (
          <optgroup label="Analyzed">
            {analyzed.map((role) => (
              <option key={role.id} value={role.id}>
                {role.name}
                {role.industry ? ` — ${role.industry}` : ""}
              </option>
            ))}
          </optgroup>
        )}
        {notAnalyzed.length > 0 && (
          <optgroup label="Not analyzed">
            {notAnalyzed.map((role) => (
              <option key={role.id} value={role.id}>
                {role.name}
                {role.industry ? ` — ${role.industry}` : ""}
              </option>
            ))}
          </optgroup>
        )}
      </select>
    </div>
  );
}

function Cell({
  item,
  children,
}: {
  item: RoleCompareItem;
  children: (analysis: NonNullable<RoleCompareItem["analysis"]>) => React.ReactNode;
}) {
  if (!item.has_analysis || !item.analysis) {
    return (
      <div className="flex h-full items-center justify-center rounded-lg border border-dashed border-border-strong bg-surface-sunken/50 px-3 py-8 text-center text-xs text-ink-muted">
        Not analyzed
      </div>
    );
  }
  return <>{children(item.analysis)}</>;
}

export function RoleComparisonPage() {
  const [roleA, setRoleA] = useState("");
  const [roleB, setRoleB] = useState("");

  const roles = useApi(() => api.listRoles({ limit: 200 }));
  const compare = useApi<{ roles: RoleCompareItem[] }>(
    () =>
      roleA && roleB
        ? api.compareRoles([roleA, roleB])
        : Promise.resolve({ roles: [] }),
    [roleA, roleB],
  );

  const options = roles.data?.items ?? [];
  const bothSelected = Boolean(roleA && roleB);
  const items = compare.data?.roles ?? [];
  const [itemA, itemB] = bothSelected ? items : [];

  return (
    <div className="animate-fade-up">
      <PageHeader
        eyebrow="Workspace"
        title="Compare Roles"
        description="Put two roles side by side to see how AI exposure, activities, and future skills differ."
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <RoleSelector label="Role A" value={roleA} roles={options} onChange={setRoleA} />
        <RoleSelector label="Role B" value={roleB} roles={options} onChange={setRoleB} />
      </div>

      {roles.loading ? (
        <Card className="mt-6">
          <div className="divide-y divide-border-faint">
            {Array.from({ length: 4 }).map((_, i) => (
              <SkeletonRow key={i} />
            ))}
          </div>
        </Card>
      ) : roles.error ? (
        <ErrorState className="mt-6" title="Could not load roles" description={roles.error} onRetry={roles.refetch} />
      ) : options.length === 0 ? (
        <div className="mt-6">
          <EmptyState
            icon={<Briefcase size={26} />}
            title="No roles to compare"
            description="Create and analyze at least one role before comparing."
            action={
              <Link to="/new-role-analysis" className="btn btn-primary">
                Analyze a new role
              </Link>
            }
          />
        </div>
      ) : !bothSelected ? (
        <div className="mt-6">
          <EmptyState
            icon={<ArrowRightLeft size={26} />}
            title="Select two roles"
            description="Choose a role from each dropdown to build a side-by-side comparison from real analysis data."
          />
        </div>
      ) : compare.loading ? (
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Skeleton className="h-96" />
          <Skeleton className="h-96" />
        </div>
      ) : compare.error ? (
        <ErrorState className="mt-6" title="Comparison failed" description={compare.error} onRetry={compare.refetch} />
      ) : itemA && itemB ? (
        <>
          {/* Comparison header */}
          <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-[1fr_auto_1fr] sm:items-stretch">
            {[itemA, itemB].map((item, index) => (
              <div
                key={index === 0 ? "role-a" : "role-b"}
                className="card card-hover flex flex-col p-5"
              >
                <p className="eyebrow">{index === 0 ? "Role A" : "Role B"}</p>
                <Link
                  to={`/role-intelligence/${item.role.id}`}
                  className="mt-1.5 text-lg font-semibold text-ink-primary hover:text-brand-700 hover:underline"
                >
                  {item.role.name}
                </Link>
                {item.role.industry && <p className="text-xs text-ink-muted">{item.role.industry}</p>}
                {item.role.description && (
                  <p className="mt-2 text-xs leading-relaxed text-ink-secondary line-clamp-3">
                    {item.role.description}
                  </p>
                )}
              </div>
            ))}
            <div className="hidden items-center justify-center sm:flex" aria-hidden="true">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-surface-sunken text-xs font-bold uppercase text-ink-muted">
                vs
              </span>
            </div>
          </div>

          {/* Impact metrics */}
          <div className="mt-6">
            <Card title="Impact metrics" subtitle="Overall scores from each role's latest analysis.">
              <div className="space-y-5">
                {[
                  { label: "AI Exposure", key: "ai_exposure" as const },
                  { label: "Automation Potential", key: "automation_score" as const },
                  { label: "Augmentation Potential", key: "augmentation_score" as const },
                ].map(({ label, key }) => (
                  <div key={label}>
                    <p className="mb-2 text-xs font-semibold text-ink-primary">{label}</p>
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                      {[itemA, itemB].map((item, index) => (
                        <div
                          key={index === 0 ? "role-a" : "role-b"}
                          className="rounded-lg border border-border-faint bg-surface-sunken px-3 py-2.5"
                        >
                          {item.analysis ? (
                            <div className="flex items-center justify-between gap-3">
                              <span className="max-w-[40%] truncate text-xs font-medium text-ink-muted">
                                {item.role.name}
                              </span>
                              <ScoreBar
                                label=""
                                value={key === "ai_exposure" ? item.analysis.ai_exposure.score : item.analysis[key]}
                                accent
                                className="flex-1"
                              />
                              {key === "ai_exposure" && (
                                <ImpactBadge level={item.analysis.ai_exposure.level} />
                              )}
                            </div>
                          ) : (
                            <p className="text-xs text-ink-muted">Not analyzed</p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}

                <div>
                  <p className="mb-2 text-xs font-semibold text-ink-primary">Reskilling Priority</p>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    {[itemA, itemB].map((item, index) => (
                      <div
                        key={index === 0 ? "role-a" : "role-b"}
                        className="rounded-lg border border-border-faint bg-surface-sunken px-3 py-2.5"
                      >
                        {item.analysis ? (
                          <div className="flex items-center justify-between gap-3">
                            <span className="truncate text-xs font-medium text-ink-muted">
                              {item.role.name}
                            </span>
                            <PriorityBadge priority={item.analysis.reskilling_priority} />
                          </div>
                        ) : (
                          <p className="text-xs text-ink-muted">Not analyzed</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </Card>
          </div>

          {/* Future skills */}
          <div className="mt-6">
            <Card title="Future skills" subtitle="Emerging skill requirements per role.">
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                {[itemA, itemB].map((item, index) => (
                  <Cell key={index === 0 ? "role-a" : "role-b"} item={item}>
                    {(analysis) => (
                      <div>
                        <p className="mb-2 text-xs font-semibold text-ink-primary">{item.role.name}</p>
                        {analysis.future_skills.length === 0 ? (
                          <p className="text-xs text-ink-muted">No future skills identified.</p>
                        ) : (
                          <ul className="space-y-2">
                            {analysis.future_skills.map((skill, index) => (
                              <li
                                key={`${skill.name}-${index}`}
                                className="flex items-center justify-between gap-2 rounded-lg border border-border-default bg-surface-card px-3 py-2 text-xs"
                              >
                                <span className="truncate font-medium text-ink-primary">
                                  {skill.name}
                                </span>
                                <span className="flex shrink-0 items-center gap-2">
                                  <span className="tabular-nums text-ink-muted">
                                    {formatPercent(skill.relevance)}
                                  </span>
                                  <PriorityBadge priority={skill.priority} />
                                </span>
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    )}
                  </Cell>
                ))}
              </div>
            </Card>
          </div>

          {/* Emerging responsibilities */}
          <div className="mt-6">
            <Card title="Emerging responsibilities" subtitle="New responsibilities expected per role.">
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                {[itemA, itemB].map((item, index) => (
                  <Cell key={index === 0 ? "role-a" : "role-b"} item={item}>
                    {(analysis) => (
                      <div>
                        <p className="mb-2 text-xs font-semibold text-ink-primary">{item.role.name}</p>
                        {analysis.future_responsibilities.length === 0 ? (
                          <p className="text-xs text-ink-muted">None identified.</p>
                        ) : (
                          <ul className="space-y-2">
                            {analysis.future_responsibilities.map((responsibility, index) => (
                              <li
                                key={`${responsibility.title}-${index}`}
                                className="rounded-lg border border-border-default bg-surface-card px-3 py-2 text-xs"
                              >
                                <p className="flex items-start gap-1.5 font-medium text-ink-primary">
                                  <TrendingUp size={13} className="mt-0.5 shrink-0 text-brand-600" aria-hidden="true" />
                                  {responsibility.title}
                                </p>
                                {responsibility.description && (
                                  <p className="mt-1 text-ink-muted">{responsibility.description}</p>
                                )}
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    )}
                  </Cell>
                ))}
              </div>
            </Card>
          </div>
        </>
      ) : null}
    </div>
  );
}
