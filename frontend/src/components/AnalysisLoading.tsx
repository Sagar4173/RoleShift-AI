import { BrainCircuit } from "lucide-react";

const STEPS = [
  "Understanding role context",
  "Analyzing activities",
  "Assessing AI impact",
  "Mapping future skills",
  "Preparing recommendations",
];

/**
 * Honest, explanatory analysis state. The backend does not stream per-stage
 * progress, so this is presented as an explanatory sequence with an
 * indeterminate progress bar — never a fabricated percentage or stage ticks.
 */
export function AnalysisLoading() {
  return (
    <div className="rounded-xl border border-brand-100 bg-brand-50 p-5" role="status">
      <div className="flex items-center gap-2.5">
        <BrainCircuit size={18} className="animate-pulse text-brand-500" aria-hidden="true" />
        <p className="text-sm font-semibold text-ink-primary">Analyzing role…</p>
      </div>

      <div
        role="progressbar"
        aria-label="Analysis in progress"
        className="mt-4 h-1.5 w-full overflow-hidden rounded-full bg-brand-100"
      >
        <div className="h-full w-1/3 animate-indeterminate rounded-full bg-brand-500" />
      </div>

      <p className="mt-4 text-xs font-medium uppercase tracking-wide text-ink-muted">
        The analysis engine processes
      </p>
      <ol className="mt-2 grid grid-cols-1 gap-x-6 gap-y-1.5 sm:grid-cols-2">
        {STEPS.map((step, index) => (
          <li key={step} className="flex items-center gap-2 text-xs text-ink-secondary">
            <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-surface-card text-[10px] font-semibold text-brand-500 shadow-card">
              {index + 1}
            </span>
            {step}
          </li>
        ))}
      </ol>

      <p className="mt-4 text-xs text-ink-muted">
        The analysis runs entirely on the backend. You'll be taken to the role's intelligence view
        when it completes.
      </p>
    </div>
  );
}
