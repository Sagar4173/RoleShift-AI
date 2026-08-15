import { AlertTriangle, RefreshCw } from "lucide-react";

import { cn } from "../../lib/utils";

interface ErrorStateProps {
  title?: string;
  description?: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({
  title = "Something went wrong",
  description = "We couldn't load this data. Please try again.",
  onRetry,
  className,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col items-center justify-center rounded-xl border border-danger-100 bg-danger-50 px-6 py-12 text-center",
        className,
      )}
    >
      <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-surface-card text-danger-600 shadow-card">
        <AlertTriangle size={22} aria-hidden="true" />
      </div>
      <h3 className="text-sm font-semibold text-ink-primary">{title}</h3>
      {description && <p className="mt-1 max-w-md text-xs leading-relaxed text-ink-secondary">{description}</p>}
      {onRetry && (
        <button type="button" onClick={onRetry} className="btn btn-secondary mt-4">
          <RefreshCw size={14} aria-hidden="true" />
          Retry
        </button>
      )}
    </div>
  );
}
