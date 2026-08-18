import { ArrowRight, Briefcase, Search, Sparkles, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { ImpactBadge } from "../components/ui/ImpactBadge";
import { PageHeader } from "../components/ui/PageHeader";
import { PriorityBadge } from "../components/ui/PriorityBadge";
import { SkeletonRow } from "../components/ui/Skeleton";
import { useAuth } from "../context/AuthContext";
import { useApi } from "../hooks/useApi";
import { formatDate } from "../lib/utils";
import { api } from "../services/api";
import type { MemberRole, RoleListItem } from "../types/api";

const CAN_ANALYZE: MemberRole[] = ["owner", "admin", "analyst"];

function RoleRow({ role }: { role: RoleListItem }) {
  return (
    <li>
      <Link
        to={`/app/role-intelligence/${role.id}`}
        className="group flex items-center justify-between gap-3 rounded-lg px-3 py-3 transition-colors hover:bg-surface-card-hover"
      >
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <p className="truncate text-sm font-medium text-ink-primary">{role.name}</p>
            {role.has_analysis ? (
              <ImpactBadge level={role.ai_exposure_level ?? "none"} />
            ) : (
              <Badge tone="neutral">Not analyzed</Badge>
            )}
          </div>
          <p className="mt-0.5 truncate text-xs text-ink-muted">
            {role.industry ?? "No industry"} · created {formatDate(role.created_at)}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {role.has_analysis && role.reskilling_priority && (
            <PriorityBadge priority={role.reskilling_priority} />
          )}
          <ArrowRight
            size={15}
            className="text-ink-muted transition-transform group-hover:translate-x-0.5 group-hover:text-brand-600"
            aria-hidden="true"
          />
        </div>
      </Link>
    </li>
  );
}

export function RoleIntelligencePage() {
  const { user } = useAuth();
  const canAnalyze = user !== null && user.role !== null && CAN_ANALYZE.includes(user.role);
  const [search, setSearch] = useState("");
  const [industry, setIndustry] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  const { data, loading, error, refetch } = useApi(
    () =>
      api.listRoles({
        search: debouncedSearch.trim() || undefined,
        industry: industry || undefined,
        limit: 200,
      }),
    [debouncedSearch, industry],
  );

  const industries = useMemo(() => {
    const values = new Set<string>();
    for (const role of data?.items ?? []) {
      if (role.industry) values.add(role.industry);
    }
    return [...values].sort((a, b) => a.localeCompare(b));
  }, [data]);

  const roles = data?.items ?? [];
  const hasAnyRoles = (data?.meta.total ?? 0) > 0;

  return (
    <div className="animate-fade-up">
      <PageHeader
        eyebrow="Workspace"
        title="Role Intelligence"
        description="Browse roles and open each role's AI exposure, activity-level impact, and future-role profile."
        actions={
          canAnalyze ? (
            <Link to="/app/new-role-analysis" className="btn btn-primary">
              <Sparkles size={14} aria-hidden="true" />
              Analyze a role
            </Link>
          ) : undefined
        }
      />

      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search
            size={16}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted"
            aria-hidden="true"
          />
          <label htmlFor="role-search" className="sr-only">
            Search roles
          </label>
          <input
            id="role-search"
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search roles… e.g. Supply Chain"
            className="input py-2 pl-9 pr-8"
          />
          {search && (
            <button
              type="button"
              onClick={() => setSearch("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-0.5 text-ink-muted hover:text-ink-primary"
              aria-label="Clear search"
            >
              <X size={14} />
            </button>
          )}
        </div>

        <div className="sm:w-56">
          <label htmlFor="industry-filter" className="sr-only">
            Filter by industry
          </label>
          <select
            id="industry-filter"
            value={industry}
            onChange={(event) => setIndustry(event.target.value)}
            className="select py-2"
          >
            <option value="">All industries</option>
            {industries.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <Card title={`Roles (${data?.meta.total ?? "…"})`}>
          <div className="divide-y divide-border-faint">
            {Array.from({ length: 6 }).map((_, i) => (
              <SkeletonRow key={i} />
            ))}
          </div>
        </Card>
      ) : error ? (
        <ErrorState title="Could not load roles" error={error} onRetry={refetch} />
      ) : roles.length === 0 ? (
        hasAnyRoles ? (
          <Card title="Roles">
            <EmptyState
              icon={<Search size={26} />}
              title="No roles match your filters"
              description="Try a different search term or industry filter."
            />
          </Card>
        ) : (
          <Card title="Roles">
            <EmptyState
              icon={<Briefcase size={26} />}
              title="No roles yet"
              description="Create and analyze a role to start building role intelligence."
              action={
                <Link to="/app/new-role-analysis" className="btn btn-primary">
                  <Sparkles size={15} aria-hidden="true" />
                  Analyze a new role
                </Link>
              }
            />
          </Card>
        )
      ) : (
        <Card title={`Roles (${data?.meta.total ?? roles.length})`}>
          <ul className="divide-y divide-border-faint">
            {roles.map((role) => (
              <RoleRow key={role.id} role={role} />
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
