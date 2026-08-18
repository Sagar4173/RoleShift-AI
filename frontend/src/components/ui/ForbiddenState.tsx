import { ShieldX } from "lucide-react";

interface ForbiddenStateProps {
  title?: string;
  description?: string;
}

export function ForbiddenState({
  title = "You don't have permission to view this",
  description = "Your role in this organization doesn't allow this action. Contact an owner or admin if you need access.",
}: ForbiddenStateProps) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center justify-center rounded-xl border border-surface-chrome-soft bg-surface-sunken px-6 py-16 text-center"
    >
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-surface-card text-ink-muted shadow-card">
        <ShieldX size={26} aria-hidden="true" />
      </div>
      <h3 className="text-base font-semibold text-ink-primary">{title}</h3>
      <p className="mt-2 max-w-md text-sm leading-relaxed text-ink-muted">{description}</p>
    </div>
  );
}