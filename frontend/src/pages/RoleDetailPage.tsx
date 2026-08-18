import { AlertTriangle, ArrowLeft, BrainCircuit, RefreshCw, ShieldAlert } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ActivityPanel } from "../components/ActivityPanel";
import { AnalysisLoading } from "../components/AnalysisLoading";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { ImpactBadge } from "../components/ui/ImpactBadge";
import { PriorityBadge } from "../components/ui/PriorityBadge";
import { RingGauge, ringColor } from "../components/ui/Metrics";
import { Skeleton } from "../components/ui/Skeleton";
import { SkillTransformation } from "../components/SkillTransformation";
import { TransformationFlow } from "../components/TransformationFlow";
import { WhyBox } from "../components/ui/WhyBox";
import { useApi } from "../hooks/useApi";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/api";
import type { ActivityImpact, MemberRole, ReskillingPriority } from "../types/api";

const RECOMMENDATION_VERB: Record<ReskillingPriority, string> = {
  critical: "Act now",
  high: "Build",
  medium: "Plan",
  low: "Monitor",
};

const CAN_ANALYZE: MemberRole[] = ["owner", "admin", "analyst"];
const CAN_FORCE: MemberRole[] = ["owner", "admin"];

function recommendationVerb(priority: ReskillingPriority): string {
  return RECOMMENDATION_VERB[priority] ?? "Recommendation";
}

function ImpactRow({
  label,
  value,
  summary,
  color,
}: {
  label: string;
  value: number;
  summary?: string;
  color?: string;
}) {
  return (
    <div className="card flex flex-col p-4">
      <div className="flex items-center justify-between">
        <p className="eyebrow">{label}</p>
        <ImpactBadge
          level={value >= 0.7 ? "high" : value >= 0.4 ? "medium" : value >= 0.2 ? "low" : "none"}
        />
      </div>
      <RingGauge value={value} size={108} strokeWidth={9} color={color} className="mx-auto mt-3" />
      {summary && (
        <WhyBox summary="Why this score" className="mt-3">
          {summary}
        </WhyBox>
      )}
    </div>
  );
}

export function RoleDetailPage() {
  const { roleId = "" } = useParams<{ roleId: string }>();
  const { user } = useAuth();
  const roleName = user?.role ?? null;
  const canAnalyze = roleName !== null && CAN_ANALYZE.includes(roleName);
  const canForce = roleName !== null && CAN_FORCE.includes(roleName);
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);

  const role = useApi(() => api.getRole(roleId), [roleId]);
  const analysis = useApi(() => api.getRoleAnalysis(roleId), [roleId]);
  const activities = useApi(() => api.listActivities(0, 200, roleId), [roleId]);

  const runAnalysis = async (force: boolean) => {
    setAnalyzing(true);
    setAnalyzeError(null);
    try {
      await api.analyzeRole(roleId, force);
      analysis.refetch();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Analysis failed";
      setAnalyzeError(message);
    } finally {
      setAnalyzing(false);
    }
  };

  if (role.loading) {
    return (
      <div>
        <Skeleton className="mb-4 h-4 w-28" />
        <div className="card p-6">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="mt-3 h-4 w-40" />
          <Skeleton className="mt-4 h-12 w-full" />
        </div>
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-48" />
          ))}
        </div>
      </div>
    );
  }

  if (role.error || !role.data) {
    return (
      <div>
        <BackLink />
        <ErrorState
          title="Role not found"
          description={
            role.error ?? "This role may have been removed, or the backend is unreachable."
          }
        />
      </div>
    );
  }

  const latest = analysis.data?.latest ?? null;
  const impacts: ActivityImpact[] = latest?.activity_impacts ?? [];

  return (
    <div className="animate-fade-up">
      <BackLink />

      <header className="card p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="eyebrow mb-1.5">Role Intelligence</p>
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-3xl font-bold tracking-tight text-ink-primary">
                {role.data.name}
              </h1>
              {latest ? (
                <ImpactBadge level={latest.ai_exposure.level} />
              ) : (
                <Badge tone="neutral">Not analyzed</Badge>
              )}
            </div>
            <p className="mt-1.5 text-sm text-ink-muted">
              {role.data.industry ? `${role.data.industry} · ` : ""}
              <span className="capitalize">{role.data.status}</span>
            </p>
            {role.data.description && (
              <p className="mt-3 max-w-3xl text-sm leading-relaxed text-ink-secondary">
                {role.data.description}
              </p>
            )}
          </div>

          <div className="flex shrink-0 items-center gap-2">
            {latest ? (
              <button
                type="button"
                onClick={() => runAnalysis(true)}
                disabled={analyzing || !canForce}
                title={canForce ? undefined : "Re-analyzing requires admin access"}
                className="btn btn-secondary"
              >
                <RefreshCw size={13} aria-hidden="true" />
                {analyzing ? "Re-analyzing…" : "Re-analyze"}
              </button>
            ) : (
              <button
                type="button"
                onClick={() => runAnalysis(false)}
                disabled={analyzing || !canAnalyze}
                title={canAnalyze ? undefined : "Analysis requires owner, admin, or analyst access"}
                className="btn btn-primary"
              >
                <BrainCircuit size={15} aria-hidden="true" />
                {analyzing ? "Analyzing…" : "Analyze Role"}
              </button>
            )}
          </div>
        </div>

        {analyzing && (
          <div className="mt-5">
            <AnalysisLoading />
          </div>
        )}
        {analyzeError && (
          <div
            role="alert"
            className="mt-4 flex items-start gap-2 rounded-lg border border-danger-100 bg-danger-50 px-3 py-2.5 text-xs text-danger-700"
          >
            <AlertTriangle size={14} className="mt-0.5 shrink-0" aria-hidden="true" />
            <span>{analyzeError}</span>
          </div>
        )}
      </header>

      {!latest ? (
        <div className="mt-6">
          <Card>
            <EmptyState
              icon={<ShieldAlert size={26} />}
              title="This role hasn't been analyzed"
              description="Run the AI pipeline against this role to persist its exposure, automation, augmentation, and future-role profile."
              action={
                <button
                  type="button"
                  onClick={() => runAnalysis(false)}
                  disabled={analyzing || !canAnalyze}
                  title={canAnalyze ? undefined : "Analysis requires owner, admin, or analyst access"}
                  className="btn btn-primary"
                >
                  <BrainCircuit size={15} aria-hidden="true" />
                  Analyze Role
                </button>
              }
            />
          </Card>
        </div>
      ) : (
        <>
          <section className="mt-8" aria-labelledby="primary-metrics">
            <div className="mb-3">
              <h2 id="primary-metrics" className="section-title">
                Intelligence metrics
              </h2>
              <p className="mt-0.5 text-xs text-ink-muted">
                Overall scores from the latest analysis.
              </p>
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <ImpactRow
                label="AI Exposure"
                value={latest.ai_exposure.score}
                summary={latest.ai_exposure.summary}
                color={ringColor(latest.ai_exposure.score)}
              />
              <ImpactRow
                label="Automation Potential"
                value={latest.automation_score}
                summary={latest.reasoning ?? undefined}
                color={ringColor(latest.automation_score)}
              />
              <ImpactRow
                label="Augmentation Potential"
                value={latest.augmentation_score}
                summary={latest.reasoning ?? undefined}
                color="#6366f1"
              />
              <div className="card flex flex-col p-4">
                <p className="eyebrow">Reskilling Priority</p>
                <div className="mt-3 flex items-center gap-3">
                  <PriorityBadge priority={latest.reskilling_priority} />
                  <span className="text-sm font-semibold text-ink-primary">
                    {latest.reskilling_priority}
                  </span>
                </div>
                <p className="mt-2 text-xs leading-relaxed text-ink-secondary">
                  {latest.ai_exposure.summary}
                </p>
                {latest.reasoning && (
                  <WhyBox summary="Why this priority" className="mt-3">
                    {latest.reasoning}
                  </WhyBox>
                )}
              </div>
            </div>
          </section>

          <section className="mt-8" aria-labelledby="activity-intelligence">
            <div className="mb-3">
              <h2 id="activity-intelligence" className="section-title">
                Activity intelligence
              </h2>
              <p className="mt-0.5 text-xs text-ink-muted">
                Which work AI can automate, augment, or should remain human-led.
              </p>
            </div>
            <ActivityPanel impacts={impacts} activities={activities.data?.items ?? []} />
          </section>

          <section className="mt-8" aria-labelledby="role-transformation">
            <div className="mb-3">
              <h2 id="role-transformation" className="section-title">
                Role transformation
              </h2>
              <p className="mt-0.5 text-xs text-ink-muted">
                How this role evolves — from today's work, through AI, to the human work of the future.
              </p>
            </div>
            <Card>
              <TransformationFlow impacts={impacts} activities={activities.data?.items ?? []} />
            </Card>
          </section>

          <section className="mt-8" aria-labelledby="skills-transformation">
            <div className="mb-3">
              <h2 id="skills-transformation" className="section-title">
                Skills transformation
              </h2>
              <p className="mt-0.5 text-xs text-ink-muted">
                Existing capability, priority reskilling needs, and the skills the role must gain.
              </p>
            </div>
            <Card>
              <SkillTransformation
                currentSkills={latest.current_skills}
                skillGaps={latest.skill_gaps}
                futureSkills={latest.future_skills}
              />
            </Card>
          </section>

          <section className="mt-8" aria-labelledby="emerging-responsibilities">
            <div className="mb-3">
              <h2 id="emerging-responsibilities" className="section-title">
                Emerging responsibilities
              </h2>
              <p className="mt-0.5 text-xs text-ink-muted">
                New responsibilities the analysis expects this role to take on.
              </p>
            </div>
            {latest.future_responsibilities.length === 0 ? (
              <Card>
                <p className="text-xs text-ink-muted">None identified in this analysis.</p>
              </Card>
            ) : (
              <ol className="grid grid-cols-1 gap-3 lg:grid-cols-3">
                {latest.future_responsibilities.map((responsibility, index) => (
                  <li key={`${responsibility.title}-${index}`} className="card card-hover p-5">
                    <p className="eyebrow">Emerging responsibility</p>
                    <h3 className="mt-1 text-sm font-semibold text-ink-primary">
                      {responsibility.title}
                    </h3>
                    {responsibility.description && (
                      <p className="mt-1.5 text-xs leading-relaxed text-ink-secondary">
                        {responsibility.description}
                      </p>
                    )}
                    {responsibility.rationale && (
                      <WhyBox summary="Why this emerges" className="mt-3">
                        {responsibility.rationale}
                      </WhyBox>
                    )}
                  </li>
                ))}
              </ol>
            )}
          </section>

          <section className="mt-8" aria-labelledby="recommendations">
            <div className="mb-3">
              <h2 id="recommendations" className="section-title">
                Recommendations
              </h2>
              <p className="mt-0.5 text-xs text-ink-muted">
                Actionable steps for workforce planning, with evidence.
              </p>
            </div>
            {latest.recommendations.length === 0 ? (
              <Card>
                <p className="text-xs text-ink-muted">No recommendations in this analysis.</p>
              </Card>
            ) : (
              <ol className="space-y-3">
                {latest.recommendations.map((recommendation, index) => (
                  <li
                    key={`${recommendation.title}-${index}`}
                    className="card card-hover flex items-start gap-4 p-5"
                  >
                    <span
                      aria-hidden="true"
                      className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-surface-accent-soft text-sm font-bold tabular-nums text-brand-400"
                    >
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="eyebrow">
                            {recommendationVerb(recommendation.priority)}
                          </p>
                          <h3 className="mt-1 text-sm font-semibold text-ink-primary">
                            {recommendation.title}
                          </h3>
                        </div>
                        <PriorityBadge priority={recommendation.priority} className="shrink-0" />
                      </div>
                      {recommendation.description && (
                        <p className="mt-1.5 text-xs leading-relaxed text-ink-secondary">
                          {recommendation.description}
                        </p>
                      )}
                      {recommendation.rationale && (
                        <WhyBox summary="Why this recommendation" className="mt-3">
                          {recommendation.rationale}
                        </WhyBox>
                      )}
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </section>

          {latest.model_metadata && (
            <p className="mt-6 text-[11px] text-ink-muted">
              Analysis by {latest.model_metadata.provider} · model {latest.model_metadata.model ?? "unknown"} ·
              prompt version {latest.model_metadata.prompt_version ?? "unknown"}
            </p>
          )}
        </>
      )}
    </div>
  );
}

function BackLink() {
  return (
    <Link
      to="/app/role-intelligence"
      className="mb-4 inline-flex items-center gap-1.5 text-xs font-medium text-ink-muted transition-colors hover:text-brand-700"
    >
      <ArrowLeft size={14} aria-hidden="true" />
      Back to roles
    </Link>
  );
}
