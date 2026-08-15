import type { ReactNode } from "react";

import { cn } from "../../lib/utils";

export type BadgeTone = "neutral" | "success" | "warning" | "danger" | "info" | "brand";

const tones: Record<BadgeTone, string> = {
  neutral: "bg-surface-sunken text-ink-secondary border border-border-default",
  success: "bg-success-50 text-success-700 border border-success-100",
  warning: "bg-warning-50 text-warning-700 border border-warning-100",
  danger: "bg-danger-50 text-danger-700 border border-danger-100",
  info: "bg-info-50 text-info-700 border border-info-100",
  brand: "bg-brand-50 text-brand-700 border border-brand-100",
};

interface BadgeProps {
  children: ReactNode;
  tone?: BadgeTone;
  className?: string;
}

export function Badge({ children, tone = "neutral", className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
