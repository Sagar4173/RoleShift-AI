import { ChevronDown, ClipboardList, UserRound } from "lucide-react";
import { useState } from "react";

import { Badge, type BadgeTone } from "./ui/Badge";
import { ScoreBar } from "./ui/Metrics";
import { WhyBox } from "./ui/WhyBox";
import type { Activity, ActivityImpact } from "../types/api";
import { cn } from "../lib/utils";

type Classification = {
  label: string;
  tone: BadgeTone;
};

function classify(automation: number, augmentation: number): Classification {
  if (automation >= 0.7) return { label: "AI can automate", tone: "danger" };
  if (augmentation >= 0.7) return { label: "AI can augment", tone: "warning" };
  return { label: "Remains human-led", tone: "success" };
}

interface ActivityPanelProps {
  impacts: ActivityImpact[];
  activities: Activity[];
  className?: string;
}

export function ActivityPanel({ impacts, activities, className }: ActivityPanelProps) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const involvementById = new Map(activities.map((activity) => [activity.id, activity.current_human_involvement]));

  if (impacts.length === 0) {
    return (
      <div className="flex flex-col items-center rounded-xl border border-dashed border-border-strong bg-surface-sunken/50 px-6 py-10 text-center">
        <ClipboardList size={22} className="text-ink-muted" aria-hidden="true" />
        <h3 className="mt-2 text-sm font-semibold text-ink-primary">No activity analysis yet</h3>
        <p className="mx-auto mt-1 max-w-md text-xs leading-relaxed text-ink-muted">
          Activity-level automation and augmentation scores appear here after the role has been
          analyzed with activities defined.
        </p>
      </div>
    );
  }

  return (
    <ul className={cn("space-y-3", className)}>
      {impacts.map((impact) => {
        const classification = classify(impact.automation_score, impact.augmentation_score);
        const humanInvolvement = involvementById.get(impact.activity_id);
        const isExpanded = expanded === impact.activity_id;
        return (
          <li key={impact.activity_id} className="card card-hover p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h4 className="text-[15px] font-semibold text-ink-primary">
                    {impact.activity_name}
                  </h4>
                  <Badge tone={classification.tone}>{classification.label}</Badge>
                </div>
                {humanInvolvement && (
                  <p className="mt-1 flex items-center gap-1 text-xs text-ink-muted">
                    <UserRound size={12} aria-hidden="true" />
                    Current human involvement:{" "}
                    <span className="font-medium text-ink-secondary">{humanInvolvement}</span>
                  </p>
                )}
              </div>
              <button
                type="button"
                onClick={() => setExpanded(isExpanded ? null : impact.activity_id)}
                aria-expanded={isExpanded}
                className="btn btn-ghost px-2.5 py-1 text-xs"
              >
                Why this activity
                <ChevronDown
                  size={14}
                  className={cn("transition-transform", isExpanded && "rotate-180")}
                  aria-hidden="true"
                />
              </button>
            </div>

            <div className="mt-4 grid grid-cols-1 gap-x-8 gap-y-2 sm:grid-cols-2">
              <ScoreBar label="Automation" value={impact.automation_score} />
              <ScoreBar label="Augmentation" value={impact.augmentation_score} />
            </div>

            {impact.human_responsibility && (
              <div className="mt-4 rounded-lg border border-success-100 bg-success-50 px-3 py-2.5">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-success-700">
                  Human responsibility
                </p>
                <p className="mt-0.5 text-sm leading-relaxed text-success-700">
                  {impact.human_responsibility}
                </p>
              </div>
            )}

            {isExpanded && impact.description && (
              <div className="mt-3">
                <WhyBox summary="Why this activity is scored this way">
                  {impact.description}
                </WhyBox>
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
