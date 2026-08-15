import { ArrowDown, ArrowRight, CheckCircle2, Lightbulb, Target } from "lucide-react";

import { PriorityBadge } from "./ui/PriorityBadge";
import { formatPercent } from "../lib/utils";
import type { CurrentSkill, FutureSkill, SkillGap } from "../types/api";
import { cn } from "../lib/utils";

interface SkillTransformationProps {
  currentSkills: CurrentSkill[];
  skillGaps: SkillGap[];
  futureSkills: FutureSkill[];
}

export function SkillTransformation({ currentSkills, skillGaps, futureSkills }: SkillTransformationProps) {
  const gapNames = new Set(skillGaps.map((gap) => gap.skill_name.toLowerCase()));
  const hasCurrentSkills = currentSkills.length > 0;

  return (
    <div>
      {/* Desktop: horizontal flow */}
      <div className="hidden md:grid md:grid-cols-[1fr_auto_1fr_auto_1fr] md:items-stretch md:gap-0">
        <Panel
          icon={<CheckCircle2 size={14} className="text-success-600" aria-hidden="true" />}
          title="Current skills"
          sublabel="Existing capability"
        >
          {currentSkills.length === 0 ? (
            <p className="text-xs text-ink-muted">No current skills linked to this role.</p>
          ) : (
            <div className="flex flex-wrap gap-1.5">
              {currentSkills.map((skill) => (
                <span
                  key={skill.name}
                  className="inline-flex items-center gap-1.5 rounded-full border border-success-100 bg-success-50 px-2.5 py-1 text-[11px] font-medium text-success-700"
                >
                  <CheckCircle2 size={11} aria-hidden="true" />
                  {skill.name}
                </span>
              ))}
            </div>
          )}
        </Panel>

        <Connector arrow={<ArrowRight />} />

        <Panel
          icon={<Target size={14} className="text-warning-600" aria-hidden="true" />}
          title="Skill gaps"
          sublabel="Priority reskilling needs"
        >
          {skillGaps.length === 0 ? (
            <p className="text-xs text-ink-muted">
              {hasCurrentSkills
                ? "No gaps — every future skill is already covered."
                : "Unable to determine — add current skills to calculate capability gaps."}
            </p>
          ) : (
            <ul className="space-y-2">
              {skillGaps.map((gap, index) => (
                <li
                  key={`${gap.skill_name}-${index}`}
                  className="rounded-lg border border-warning-100 bg-warning-50 p-2.5"
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-xs font-medium text-ink-primary">{gap.skill_name}</p>
                    <PriorityBadge priority={gap.priority} />
                  </div>
                  {gap.category && <p className="mt-0.5 text-[11px] text-ink-muted">{gap.category}</p>}
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Connector arrow={<ArrowRight />} />

        <Panel
          icon={<Lightbulb size={14} className="text-brand-600" aria-hidden="true" />}
          title="Future skills"
          sublabel="Emerging capability"
        >
          {futureSkills.length === 0 ? (
            <p className="text-xs text-ink-muted">No future skills identified.</p>
          ) : (
            <ul className="space-y-2">
              {futureSkills.map((skill, index) => (
                <li key={`${skill.name}-${index}`} className="text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium text-ink-primary">
                      {skill.name}
                      {hasCurrentSkills && !gapNames.has(skill.name.toLowerCase()) && (
                        <span className="ml-1.5 text-[10px] font-semibold uppercase tracking-wide text-success-600">
                          covered
                        </span>
                      )}
                    </span>
                    <span className="shrink-0 tabular-nums text-ink-muted">
                      {formatPercent(skill.relevance)}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>

      {/* Mobile: vertical flow */}
      <div className="md:hidden">
        <Panel
          icon={<CheckCircle2 size={14} className="text-success-600" aria-hidden="true" />}
          title="Current skills"
          sublabel="Existing capability"
        >
          {currentSkills.length === 0 ? (
            <p className="text-xs text-ink-muted">No current skills linked to this role.</p>
          ) : (
            <div className="flex flex-wrap gap-1.5">
              {currentSkills.map((skill) => (
                <span
                  key={skill.name}
                  className="inline-flex items-center gap-1.5 rounded-full border border-success-100 bg-success-50 px-2.5 py-1 text-[11px] font-medium text-success-700"
                >
                  <CheckCircle2 size={11} aria-hidden="true" />
                  {skill.name}
                </span>
              ))}
            </div>
          )}
        </Panel>
        <Connector arrow={<ArrowDown />} vertical />
        <Panel
          icon={<Target size={14} className="text-warning-600" aria-hidden="true" />}
          title="Skill gaps"
          sublabel="Priority reskilling needs"
        >
          {skillGaps.length === 0 ? (
            <p className="text-xs text-ink-muted">
              {hasCurrentSkills
                ? "No gaps — every future skill is already covered."
                : "Unable to determine — add current skills to calculate capability gaps."}
            </p>
          ) : (
            <ul className="space-y-2">
              {skillGaps.map((gap, index) => (
                <li
                  key={`${gap.skill_name}-${index}`}
                  className="rounded-lg border border-warning-100 bg-warning-50 p-2.5"
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-xs font-medium text-ink-primary">{gap.skill_name}</p>
                    <PriorityBadge priority={gap.priority} />
                  </div>
                  {gap.category && <p className="mt-0.5 text-[11px] text-ink-muted">{gap.category}</p>}
                </li>
              ))}
            </ul>
          )}
        </Panel>
        <Connector arrow={<ArrowDown />} vertical />
        <Panel
          icon={<Lightbulb size={14} className="text-brand-600" aria-hidden="true" />}
          title="Future skills"
          sublabel="Emerging capability"
        >
          {futureSkills.length === 0 ? (
            <p className="text-xs text-ink-muted">No future skills identified.</p>
          ) : (
            <ul className="space-y-2">
              {futureSkills.map((skill, index) => (
                <li key={`${skill.name}-${index}`} className="text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium text-ink-primary">{skill.name}</span>
                    <span className="shrink-0 tabular-nums text-ink-muted">
                      {formatPercent(skill.relevance)}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>
    </div>
  );
}

function Panel({
  icon,
  title,
  sublabel,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  sublabel: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-border-default bg-surface-card p-4 shadow-card">
      <div className="flex items-center gap-2">
        {icon}
        <div>
          <p className="text-xs font-semibold text-ink-primary">{title}</p>
          <p className="text-[11px] text-ink-muted">{sublabel}</p>
        </div>
      </div>
      <div className="mt-3">{children}</div>
    </div>
  );
}

function Connector({ arrow, vertical }: { arrow: React.ReactNode; vertical?: boolean }) {
  return (
    <div
      className={cn(
        "flex items-center justify-center text-ink-muted",
        vertical ? "py-1" : "px-2",
      )}
      aria-hidden="true"
    >
      {arrow}
    </div>
  );
}
