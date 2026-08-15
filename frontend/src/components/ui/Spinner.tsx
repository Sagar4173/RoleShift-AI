import { Loader2 } from "lucide-react";

import { cn } from "../../lib/utils";

interface SpinnerProps {
  label?: string;
  className?: string;
}

export function Spinner({ label, className }: SpinnerProps) {
  return (
    <div
      role="status"
      className={cn("flex items-center gap-2.5 text-sm text-ink-muted", className)}
    >
      <Loader2 size={18} className="animate-spin text-brand-600" aria-hidden="true" />
      {label && <span>{label}</span>}
      <span className="sr-only">Loading</span>
    </div>
  );
}
