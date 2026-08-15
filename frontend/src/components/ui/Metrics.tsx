import type { ReactNode } from "react";

import { formatPercent } from "../../lib/utils";
import { cn } from "../../lib/utils";

export function ringColor(value: number): string {
  if (value >= 0.7) return "#fb7185";
  if (value >= 0.4) return "#fbbf24";
  if (value >= 0.2) return "#7dd3fc";
  return "#64748b";
}

interface RingGaugeProps {
  value: number;
  size?: number;
  strokeWidth?: number;
  color?: string;
  className?: string;
}

export function RingGauge({ value, size = 120, strokeWidth = 10, color, className }: RingGaugeProps) {
  const clamped = Math.max(0, Math.min(1, value));
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const filled = clamped * circumference;
  const gaugeColor = color ?? ringColor(clamped);

  return (
    <div className={cn("relative inline-flex items-center justify-center", className)}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img">
        <title>Score gauge</title>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--border-faint)"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={gaugeColor}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={`${filled} ${circumference}`}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          style={{ transition: "stroke-dasharray 600ms var(--ease-out)" }}
        />
      </svg>
      <span className="absolute text-xl font-semibold tabular-nums text-ink-primary">
        {formatPercent(clamped)}
      </span>
    </div>
  );
}

interface MetricTileProps {
  label: string;
  value: number;
  sublabel?: string;
  icon?: ReactNode;
  color?: string;
  className?: string;
}

export function MetricTile({ label, value, sublabel, icon, color, className }: MetricTileProps) {
  return (
    <div className={cn("card flex items-center gap-4 p-5", className)}>
      <RingGauge value={value} size={104} strokeWidth={9} color={color} />
      <div className="min-w-0">
        <div className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-ink-muted">
          {icon && <span className="text-ink-muted">{icon}</span>}
          {label}
        </div>
        <p className="mt-1.5 text-sm font-semibold text-ink-primary">
          {formatPercent(value)} impact
        </p>
        {sublabel && <p className="mt-0.5 text-xs text-ink-muted">{sublabel}</p>}
      </div>
    </div>
  );
}

interface ScoreBarProps {
  label: string;
  value: number;
  accent?: boolean;
  className?: string;
}

export function ScoreBar({ label, value, accent, className }: ScoreBarProps) {
  const clamped = Math.max(0, Math.min(1, value));
  const color = accent ? "#6366f1" : ringColor(clamped);
  return (
    <div className={cn("flex items-center gap-3", className)}>
      {label && (
        <span className="w-32 shrink-0 truncate text-xs font-medium text-ink-secondary">{label}</span>
      )}
      <div
        className="h-2 flex-1 overflow-hidden rounded-full bg-surface-sunken"
        role="progressbar"
        aria-valuenow={Math.round(clamped * 100)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label || "score"}
      >
        <div
          className="h-full rounded-full transition-[width] duration-500"
          style={{ width: `${clamped * 100}%`, backgroundColor: color }}
        />
      </div>
      <span className="w-10 shrink-0 text-right text-xs font-medium tabular-nums text-ink-primary">
        {formatPercent(clamped)}
      </span>
    </div>
  );
}
