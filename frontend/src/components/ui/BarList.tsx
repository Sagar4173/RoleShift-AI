import type { ReskillingPriority } from "../../types/api";
import { formatPercent, priorityRank } from "../../lib/utils";
import { cn } from "../../lib/utils";
import { PriorityBadge } from "./PriorityBadge";

interface BarListRow {
  label: string;
  value: number;
  meta?: string;
  priority?: ReskillingPriority;
}

interface BarListProps {
  rows: BarListRow[];
  emptyText?: string;
  className?: string;
}

export function BarList({ rows, emptyText = "No data yet.", className }: BarListProps) {
  if (rows.length === 0) {
    return <p className="text-xs text-ink-muted">{emptyText}</p>;
  }

  const max = Math.max(...rows.map((row) => row.value), 0.01);

  return (
    <ul className={cn("space-y-3", className)}>
      {rows.map((row) => (
        <li key={row.label}>
          <div className="flex items-baseline justify-between gap-2">
            <span className="truncate text-xs font-medium text-ink-primary">{row.label}</span>
            <span className="flex shrink-0 items-center gap-2">
              {row.priority && <PriorityBadge priority={row.priority} />}
              <span className="w-9 text-right text-xs font-medium tabular-nums text-ink-secondary">
                {formatPercent(row.value)}
              </span>
            </span>
          </div>
          <div className="mt-1 h-2 overflow-hidden rounded-full bg-surface-sunken">
            <div
              className="h-full rounded-full bg-brand-500"
              style={{ width: `${(row.value / max) * 100}%`, transition: "width 500ms var(--ease-out)" }}
            />
          </div>
          {row.meta && <p className="mt-0.5 text-[11px] text-ink-muted">{row.meta}</p>}
        </li>
      ))}
    </ul>
  );
}

export function sortByPriority(a: ReskillingPriority, b: ReskillingPriority): number {
  return priorityRank(b) - priorityRank(a);
}
