import { ArrowDown, ArrowRight, Check, Cpu, TrendingUp, UserRound } from "lucide-react";

import { Badge, type BadgeTone } from "./ui/Badge";
import type { Activity, ActivityImpact } from "../types/api";
import { cn } from "../lib/utils";

function classify(automation: number, augmentation: number): { label: string; tone: BadgeTone } {
  if (automation >= 0.7) return { label: "AI can automate", tone: "danger" };
  if (augmentation >= 0.7) return { label: "AI can augment", tone: "warning" };
  return { label: "Remains human-led", tone: "success" };
}

interface SegmentProps {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
  className?: string;
}

function Segment({ icon, title, children, className }: SegmentProps) {
  return (
    <div className={cn("rounded-xl border border-border-default bg-surface-card p-4 shadow-card", className)}>
      <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
        {icon}
        {title}
      </p>
      <div className="mt-2 text-sm">{children}</div>
    </div>
  );
}

function TransformationRow({
  impact,
  activity,
  index,
}: {
  impact: ActivityImpact;
  activity?: Activity;
  index: number;
}) {
  const classification = classify(impact.automation_score, impact.augmentation_score);

  const current = (
    <Segment icon={<UserRound size={12} className="text-ink-muted" aria-hidden="true" />} title="Current work">
      <p className="font-medium text-ink-primary">{impact.activity_name}</p>
      {activity?.current_human_involvement && (
        <p className="mt-0.5 text-xs text-ink-muted">
          Human involvement:{" "}
          <span className="font-medium text-ink-secondary">{activity.current_human_involvement}</span>
        </p>
      )}
    </Segment>
  );

  const transformation = (
    <Segment
      icon={<Cpu size={12} className="text-brand-600" aria-hidden="true" />}
      title="AI transformation"
    >
      <Badge tone={classification.tone}>{classification.label}</Badge>
      <p className="mt-2 text-xs leading-relaxed text-ink-secondary">
        {impact.description?.trim() || "AI analysis completed for this activity."}
      </p>
    </Segment>
  );

  const future = (
    <Segment
      icon={<TrendingUp size={12} className="text-brand-600" aria-hidden="true" />}
      title="Future work"
    >
      <p className="text-xs leading-relaxed text-ink-secondary">
        {impact.human_responsibility?.trim() ||
          "Human oversight and judgment remain on this activity."}
      </p>
    </Segment>
  );

  return (
    <li
      aria-label={`Transformation path for ${impact.activity_name}`}
      className="rounded-xl border border-border-default bg-surface-sunken p-4"
    >
      <p className="mb-3 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
        <span className="flex h-5 w-5 items-center justify-center rounded-md bg-brand-600 text-[10px] font-bold text-white">
          {index + 1}
        </span>
        {impact.activity_name}
      </p>

      {/* Desktop: horizontal flow */}
      <div className="hidden md:grid md:grid-cols-[1fr_auto_1fr_auto_1fr] md:items-stretch md:gap-0">
        {current}
        <div className="flex items-center justify-center px-2">
          <ArrowRight size={18} className="text-ink-muted" aria-hidden="true" />
        </div>
        {transformation}
        <div className="flex items-center justify-center px-2">
          <ArrowRight size={18} className="text-ink-muted" aria-hidden="true" />
        </div>
        {future}
      </div>

      {/* Mobile: vertical flow */}
      <div className="space-y-0 md:hidden">
        {current}
        <div className="flex justify-center py-1">
          <ArrowDown size={16} className="text-ink-muted" aria-hidden="true" />
        </div>
        {transformation}
        <div className="flex justify-center py-1">
          <ArrowDown size={16} className="text-ink-muted" aria-hidden="true" />
        </div>
        {future}
      </div>
    </li>
  );
}

interface TransformationFlowProps {
  impacts: ActivityImpact[];
  activities: Activity[];
}

export function TransformationFlow({ impacts, activities }: TransformationFlowProps) {
  const activitiesById = new Map(activities.map((activity) => [activity.id, activity]));

  if (impacts.length === 0) {
    return (
      <div className="flex flex-col items-center rounded-xl border border-dashed border-border-strong bg-surface-sunken/50 px-6 py-10 text-center">
        <Check size={20} className="text-ink-muted" aria-hidden="true" />
        <p className="mt-2 text-sm font-medium text-ink-primary">No transformation paths yet</p>
        <p className="mt-1 max-w-md text-xs text-ink-muted">
          Activity-level transformation paths appear once the role has been analyzed with
          activities defined.
        </p>
      </div>
    );
  }

  return (
    <ol className="space-y-4">
      {impacts.map((impact, index) => (
        <TransformationRow
          key={impact.activity_id}
          impact={impact}
          activity={activitiesById.get(impact.activity_id)}
          index={index}
        />
      ))}
    </ol>
  );
}
