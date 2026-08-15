import type { ImpactLevel } from "../../types/api";
import { IMPACT_LEVEL_LABEL } from "../../lib/utils";
import { cn } from "../../lib/utils";

const LEVEL_COLORS: Record<ImpactLevel, string> = {
  none: "#94a3b8",
  low: "#34d399",
  medium: "#fbbf24",
  high: "#fb7185",
};

export interface DonutSlice {
  level: ImpactLevel;
  count: number;
}

interface DonutChartProps {
  data: DonutSlice[];
  size?: number;
  className?: string;
}

export function DonutChart({ data, size = 180, className }: DonutChartProps) {
  const total = data.reduce((sum, slice) => sum + slice.count, 0);
  const stroke = 22;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;

  let offset = 0;
  const segments = data.map((slice) => {
    const fraction = total > 0 ? slice.count / total : 0;
    const dash = fraction * circumference;
    const segment = {
      level: slice.level,
      count: slice.count,
      dash,
      offset,
    };
    offset += dash;
    return segment;
  });

  return (
    <div className={cn("flex items-center gap-6", className)}>
      <div className="relative inline-flex shrink-0 items-center justify-center">
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img">
          <title>AI impact distribution</title>
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="var(--border-faint)"
            strokeWidth={stroke}
          />
          {segments.map((segment) =>
            segment.dash > 0 ? (
              <circle
                key={segment.level}
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="none"
                stroke={LEVEL_COLORS[segment.level]}
                strokeWidth={stroke}
                strokeDasharray={`${segment.dash} ${circumference - segment.dash}`}
                strokeDashoffset={-segment.offset}
                transform={`rotate(-90 ${size / 2} ${size / 2})`}
                style={{ transition: "stroke-dasharray 600ms var(--ease-out)" }}
              />
            ) : null,
          )}
        </svg>
        <div className="absolute text-center">
          <p className="metric-value">{total}</p>
          <p className="text-[11px] text-ink-muted">roles</p>
        </div>
      </div>

      <ul className="min-w-0 flex-1 space-y-1.5">
        {data.map((slice) => (
          <li key={slice.level} className="flex items-center gap-2 text-xs text-ink-secondary">
            <span
              className="h-2.5 w-2.5 shrink-0 rounded-full"
              style={{ backgroundColor: LEVEL_COLORS[slice.level] }}
              aria-hidden="true"
            />
            <span className="w-16 shrink-0 font-medium text-ink-primary">
              {IMPACT_LEVEL_LABEL[slice.level]}
            </span>
            <span className="tabular-nums text-ink-muted">{slice.count}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
