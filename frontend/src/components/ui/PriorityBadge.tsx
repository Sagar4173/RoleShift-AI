import type { ReskillingPriority } from "../../types/api";
import { RESKILLING_LABEL } from "../../lib/utils";
import { cn } from "../../lib/utils";

const CONFIG: Record<ReskillingPriority, { tone: string; dot: string }> = {
  low: { tone: "bg-surface-sunken text-ink-secondary border border-border-default", dot: "bg-ink-muted" },
  medium: { tone: "bg-info-50 text-info-700 border border-info-100", dot: "bg-info-600" },
  high: { tone: "bg-warning-50 text-warning-700 border border-warning-100", dot: "bg-warning-600" },
  critical: { tone: "bg-danger-50 text-danger-700 border border-danger-100", dot: "bg-danger-600" },
};

interface PriorityBadgeProps {
  priority: ReskillingPriority;
  className?: string;
}

export function PriorityBadge({ priority, className }: PriorityBadgeProps) {
  const config = CONFIG[priority] ?? CONFIG.low;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium",
        config.tone,
        className,
      )}
    >
      <span className={cn("h-1.5 w-1.5 shrink-0 rounded-full", config.dot)} aria-hidden="true" />
      {RESKILLING_LABEL[priority] ?? priority}
    </span>
  );
}
