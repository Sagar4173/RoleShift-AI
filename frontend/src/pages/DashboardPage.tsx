import {
  ArrowRight,
  BrainCircuit,
  Briefcase,
  Cpu,
  GraduationCap,
  Gauge,
  ListChecks,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { Link } from "react-router-dom";

import { Card } from "../components/ui/Card";
import { DonutChart } from "../components/ui/DonutChart";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { BarList } from "../components/ui/BarList";
import { PageHeader } from "../components/ui/PageHeader";
import { Skeleton, SkeletonCard } from "../components/ui/Skeleton";
import { StatCard } from "../components/ui/StatCard";
import { ImpactBadge } from "../components/ui/ImpactBadge";
import { PriorityBadge } from "../components/ui/PriorityBadge";
import { useApi } from "../hooks/useApi";
import { useAuth } from "../context/AuthContext";
import { formatDate, formatPercent } from "../lib/utils";
import { api } from "../services/api";
import type { RecentRoleAnalysisItem } from "../types/api";

function KpiSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}

function TopOpportunities({
  items,
}: {
  items: RecentRoleAnalysisItem[];
}) {
  const ranked = [...items].sort((a, b) => b.ai_exposure_score - a.ai_exposure_score).slice(0, 5);
  return (
    <ol className="space-y-1">
      {ranked.map((item, index) => (
        <li key={item.role_id}>
          <Link
            to={`/app/role-intelligence/${item.role_id}`}
            className="group flex items-center gap-3 rounded-lg px-2 py-2.5 transition-colors hover:bg-surface-card-hover"
          >
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-surface-sunken text-[11px] font-semibold tabular-nums text-ink-muted">
              {index + 1}
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <p className="truncate text-sm font-medium text-ink-primary">{item.role_name}</p>
                <ImpactBadge level={item.ai_exposure_level} />
              </div>
              <p className="mt-0.5 truncate text-xs text-ink-muted">
                {item.industry ?? "No industry"} · automation {formatPercent(item.automation_score)}
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <span className="text-sm font-semibold tabular-nums text-ink-primary">
                {formatPercent(item.ai_exposure_score)}
              </span>
              <ArrowRight
                size={15}
                className="text-ink-muted transition-transform group-hover:translate-x-0.5 group-hover:text-brand-600"
                aria-hidden="true"
              />
            </div>
          </Link>
        </li>
      ))}
    </ol>
  );
}

export function DashboardPage() {
  const { user } = useAuth();
  const canAnalyze = user?.role !== null && user?.role !== undefined && ["owner", "admin", "analyst"].includes(user.role);

  const summary = useApi(() => api.getDashboardSummary());
  const activities = useApi(() => api.listActivities(0, 1));

  const loading = summary.loading || activities.loading;

  if (loading) {
    return (
      <div>
        <PageHeader title="Workforce AI Intelligence" description="Loading workforce intelligence…" />
        <KpiSkeleton />
        <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Skeleton className="h-80" />
          <Skeleton className="h-80" />
        </div>
      </div>
    );
  }

  if (summary.error || !summary.data) {
    return (
      <div>
        <PageHeader
          eyebrow="Overview"
          title="Workforce AI Intelligence"
          description="AI exposure across your workforce: what will change, what stays human, and what to do about it."
        />
        <ErrorState
          title="Dashboard unavailable"
          description={summary.error ?? "Could not load dashboard data."}
          onRetry={summary.refetch}
        />
      </div>
    );
  }

  const data = summary.data;
  const hasAnalysis = data.roles_analyzed > 0;
  const analyzedShare =
    data.total_roles > 0 ? Math.round((data.roles_analyzed / data.total_roles) * 100) : 0;

  return (
    <div className="animate-fade-up">
      <PageHeader
        eyebrow="Overview"
        title="Workforce AI Intelligence"
        description="Understand how AI transforms your workforce: which roles carry the highest exposure, which skills are becoming essential, and where to act first."
        actions={
          canAnalyze ? (
            <Link to="/app/new-role-analysis" className="btn btn-primary">
              <Sparkles size={14} aria-hidden="true" />
              New Role Analysis
            </Link>
          ) : undefined
        }
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Roles"
          value={data.total_roles}
          icon={<Briefcase size={16} />}
          iconTone="brand"
          hint={hasAnalysis ? `${data.roles_analyzed} analyzed (${analyzedShare}%)` : "No analyses yet"}
        />
        <StatCard
          label="Activities"
          value={activities.data?.meta.total ?? 0}
          icon={<ListChecks size={16} />}
          iconTone="info"
          hint="Work items in the workspace"
        />
        <StatCard
          label="High-impact roles"
          value={data.high_ai_impact_roles}
          icon={<ShieldAlert size={16} />}
          iconTone="danger"
          hint="Highest AI exposure"
        />
        <StatCard
          label="Reskilling demand"
          value={data.high_reskilling_priority_roles}
          icon={<GraduationCap size={16} />}
          iconTone="warning"
          hint="Roles flagged for priority reskilling"
        />
      </div>

      {!hasAnalysis ? (
        <div className="mt-6">
          <Card>
            <EmptyState
              icon={<BrainCircuit size={26} />}
              title="Analyze your first role"
              description="Enter a role (e.g. Supply Chain Manager) and RoleShift AI will run a real AI analysis, then build its intelligence view here."
              action={
                canAnalyze ? (
                  <Link to="/app/new-role-analysis" className="btn btn-primary">
                    <Sparkles size={15} aria-hidden="true" />
                    Analyze a new role
                  </Link>
                ) : undefined
              }
            />
          </Card>
        </div>
      ) : (
        <>
          <section className="mt-8" aria-labelledby="transformation-overview">
            <div className="mb-3 flex items-center gap-2">
              <Gauge size={16} className="text-brand-600" aria-hidden="true" />
              <h2 id="transformation-overview" className="section-title">
                AI Transformation Overview
              </h2>
            </div>
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              <Card title="AI impact distribution" subtitle="Analyzed roles by overall exposure level.">
                <DonutChart
                  data={data.ai_impact_distribution.map((item) => ({
                    level: item.level,
                    count: item.count,
                  }))}
                />
              </Card>
              <Card
                title="Workload automation signal"
                subtitle="High-automation activities across analyzed roles."
                className="lg:col-span-2"
              >
                <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
                  <div className="flex flex-col items-center justify-center rounded-xl border border-border-default bg-surface-sunken/50 p-5">
                    <Cpu size={20} className="text-brand-600" aria-hidden="true" />
                    <p className="metric-value mt-2">{data.high_automation_activities}</p>
                    <p className="mt-1 text-center text-xs text-ink-muted">
                      activities where AI can take over most of the work
                    </p>
                  </div>
                  <div className="flex flex-col items-center justify-center rounded-xl border border-border-default bg-surface-sunken/50 p-5">
                    <BrainCircuit size={20} className="text-brand-600" aria-hidden="true" />
                    <p className="metric-value mt-2">{data.high_ai_impact_roles}</p>
                    <p className="mt-1 text-center text-xs text-ink-muted">
                      roles with high AI exposure
                    </p>
                  </div>
                  <div className="flex flex-col items-center justify-center rounded-xl border border-border-default bg-surface-sunken/50 p-5">
                    <GraduationCap size={20} className="text-brand-600" aria-hidden="true" />
                    <p className="metric-value mt-2">{data.high_reskilling_priority_roles}</p>
                    <p className="mt-1 text-center text-xs text-ink-muted">
                      roles requiring priority reskilling
                    </p>
                  </div>
                </div>
              </Card>
            </div>
          </section>

          <section className="mt-8" aria-labelledby="top-opportunities">
            <div className="mb-3 flex items-center gap-2">
              <ShieldAlert size={16} className="text-brand-600" aria-hidden="true" />
              <h2 id="top-opportunities" className="section-title">
                Top Transformation Opportunities
              </h2>
            </div>
            <Card
              title="Highest-exposure roles"
              subtitle="Ranked by overall AI exposure — investigate these first."
            >
              {data.recent_role_analyses.length === 0 ? (
                <p className="text-xs text-ink-muted">No analyzed roles yet.</p>
              ) : (
                <TopOpportunities items={data.recent_role_analyses} />
              )}
            </Card>
          </section>

          <section className="mt-8" aria-labelledby="future-skills">
            <div className="mb-3 flex items-center gap-2">
              <GraduationCap size={16} className="text-brand-600" aria-hidden="true" />
              <h2 id="future-skills" className="section-title">
                Future Skills
              </h2>
            </div>
            <Card
              title="Rising skill demand"
              subtitle="Most demanded future skills across analyzed roles."
            >
              <BarList
                rows={data.top_future_skills.map((skill) => ({
                  label: skill.name,
                  value: skill.relevance,
                  priority: skill.priority,
                  meta: skill.roles > 1 ? `Required by ${skill.roles} roles` : "1 role",
                }))}
                emptyText="No future skills have been identified yet."
              />
            </Card>
          </section>

          <section className="mt-8" aria-labelledby="recent-analyses">
            <div className="mb-3 flex items-center gap-2">
              <BrainCircuit size={16} className="text-brand-600" aria-hidden="true" />
              <h2 id="recent-analyses" className="section-title">
                Recent Analyses
              </h2>
            </div>
            <Card title="Latest intelligence" subtitle="Produced by the analysis engine.">
              {data.recent_role_analyses.length === 0 ? (
                <p className="text-xs text-ink-muted">No analyses recorded yet.</p>
              ) : (
                <ul className="divide-y divide-border-faint">
                  {data.recent_role_analyses.map((item) => (
                    <li key={item.role_id}>
                      <Link
                        to={`/app/role-intelligence/${item.role_id}`}
                        className="group flex items-center justify-between gap-3 py-3 transition-colors hover:bg-surface-card-hover"
                      >
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <p className="truncate text-sm font-medium text-ink-primary">
                              {item.role_name}
                            </p>
                            <ImpactBadge level={item.ai_exposure_level} />
                          </div>
                          <p className="mt-0.5 text-xs text-ink-muted">
                            {item.industry ?? "No industry"} · analyzed {formatDate(item.analyzed_at)} ·{" "}
                            {item.activity_count} activities · {item.future_skills_count} future skills
                          </p>
                        </div>
                        <div className="flex shrink-0 items-center gap-2">
                          <PriorityBadge priority={item.reskilling_priority} />
                          <ArrowRight
                            size={15}
                            className="text-ink-muted transition-transform group-hover:translate-x-0.5 group-hover:text-brand-600"
                            aria-hidden="true"
                          />
                        </div>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </section>
        </>
      )}
    </div>
  );
}
