import type { ReactNode } from "react";

import { cn } from "../../lib/utils";

interface StatCardProps {
  label: string;
  value: string | number;
  hint?: string;
  icon?: ReactNode;
  iconTone?: "brand" | "success" | "warning" | "danger" | "info" | "neutral";
  className?: string;
}

const iconTones: Record<NonNullable<StatCardProps["iconTone"]>, string> = {
  brand: "bg-brand-50 text-brand-600",
  success: "bg-success-50 text-success-600",
  warning: "bg-warning-50 text-warning-600",
  danger: "bg-danger-50 text-danger-600",
  info: "bg-info-50 text-info-600",
  neutral: "bg-surface-sunken text-ink-muted",
};

export function StatCard({ label, value, hint, icon, iconTone = "brand", className }: StatCardProps) {
  return (
    <div className={cn("card p-5", className)}>
      <div className="flex items-center justify-between gap-3">
        <p className="eyebrow">{label}</p>
        {icon && (
          <div
            className={cn("flex h-8 w-8 shrink-0 items-center justify-center rounded-lg", iconTones[iconTone])}
            aria-hidden="true"
          >
            {icon}
          </div>
        )}
      </div>
      <p className="metric-value mt-3">{value}</p>
      {hint && <p className="mt-1.5 text-xs text-ink-muted">{hint}</p>}
    </div>
  );
}
