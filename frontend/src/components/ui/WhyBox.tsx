import type { ReactNode } from "react";

import { cn } from "../../lib/utils";

interface WhyBoxProps {
  summary?: string;
  children: ReactNode;
  className?: string;
}

/**
 * Accessible explainability disclosure ("Why?"). Uses a native <details>
 * element so it works with keyboard navigation and screen readers.
 */
export function WhyBox({ summary = "Why?", children, className }: WhyBoxProps) {
  return (
    <details
      className={cn(
        "group rounded-lg border border-border-default bg-surface-sunken/60 transition-colors open:bg-surface-sunken",
        className,
      )}
    >
      <summary className="flex cursor-pointer select-none items-center gap-1.5 px-3 py-2 text-xs font-medium text-brand-400 hover:text-brand-300">
        <span
          aria-hidden="true"
          className="inline-flex h-4 w-4 items-center justify-center rounded-full bg-brand-100 text-[10px] font-bold text-brand-700 transition-transform group-open:rotate-45"
        >
          +
        </span>
        {summary}
      </summary>
      <div className="border-t border-border-default px-3 py-2.5 text-xs leading-relaxed text-ink-secondary">
        {children}
      </div>
    </details>
  );
}
