import { AlertTriangle, ArrowUp, CircleSlash, Minus } from "lucide-react";

import type { ImpactLevel } from "../../types/api";
import { IMPACT_LEVEL_LABEL } from "../../lib/utils";
import { cn } from "../../lib/utils";

const CONFIG: Record<
  ImpactLevel,
  { tone: string; icon: typeof Minus }
> = {
  none: { tone: "bg-surface-sunken text-ink-secondary border border-border-default", icon: CircleSlash },
  low: { tone: "bg-success-50 text-success-700 border border-success-100", icon: Minus },
  medium: { tone: "bg-warning-50 text-warning-700 border border-warning-100", icon: ArrowUp },
  high: { tone: "bg-danger-50 text-danger-700 border border-danger-100", icon: AlertTriangle },
};

interface ImpactBadgeProps {
  level: ImpactLevel;
  className?: string;
}

export function ImpactBadge({ level, className }: ImpactBadgeProps) {
  const config = CONFIG[level] ?? CONFIG.none;
  const Icon = config.icon;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
        config.tone,
        className,
      )}
    >
      <Icon size={12} aria-hidden="true" />
      {IMPACT_LEVEL_LABEL[level] ?? "None"}
    </span>
  );
}
