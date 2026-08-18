import { AlertTriangle, RefreshCw } from "lucide-react";

import { describeApiError } from "../../lib/apiErrors";
import type { ApiError } from "../../services/api";
import { cn } from "../../lib/utils";

interface ErrorStateProps {
  title?: string;
  description?: string;
  error?: ApiError | null;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({
  title = "Something went wrong",
  description = "We couldn't load this data. Please try again.",
  error,
  onRetry,
  className,
}: ErrorStateProps) {
  const apiDescription = describeApiError(error);
  const message = error ? apiDescription.message || description : description;
  const details = error ? apiDescription.details : [];

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
      {message && <p className="mt-1 max-w-md text-xs leading-relaxed text-ink-secondary">{message}</p>}
      {details.length > 0 && (
        <ul className="mt-2 max-w-md list-disc space-y-1 pl-5 text-left text-xs leading-relaxed text-ink-secondary">
          {details.map((detail, index) => (
            <li key={index}>{detail}</li>
          ))}
        </ul>
      )}
      {onRetry && (
        <button type="button" onClick={onRetry} className="btn btn-secondary mt-4">
          <RefreshCw size={14} aria-hidden="true" />
          Retry
        </button>
      )}
    </div>
  );
}
