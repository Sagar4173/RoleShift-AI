import { BrainCircuit, Info, Plus, Sparkles, Trash2 } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { AnalysisLoading } from "../components/AnalysisLoading";
import { Card } from "../components/ui/Card";
import { ErrorState } from "../components/ui/ErrorState";
import { ForbiddenState } from "../components/ui/ForbiddenState";
import { PageHeader } from "../components/ui/PageHeader";
import { useAuth } from "../context/AuthContext";
import { api, ApiError } from "../services/api";

const INDUSTRY_SUGGESTIONS = [
  "Technology / SaaS",
  "Manufacturing",
  "Financial Services",
  "Healthcare",
  "Retail",
  "Logistics",
  "Energy",
  "Education",
  "Government",
  "Professional Services",
];

interface ProcessDraft {
  name: string;
  description: string;
  activities: string;
}

function splitLines(value: string): string[] {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
}

function splitCommaSeparated(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

function SectionHeading({ step, children }: { step: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2.5">
      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-brand-600 text-[11px] font-bold text-white">
        {step}
      </span>
      <h3 className="text-sm font-semibold text-ink-primary">{children}</h3>
    </div>
  );
}

export function NewRoleAnalysisPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const role = user?.role ?? null;
  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("");
  const [description, setDescription] = useState("");
  const [processes, setProcesses] = useState<ProcessDraft[]>([
    { name: "", description: "", activities: "" },
  ]);
  const [currentSkills, setCurrentSkills] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const hasValidProcesses = processes.some(
    (process) =>
      process.name.trim().length > 0 && splitLines(process.activities).length > 0
  );
  const canSubmit =
    name.trim().length > 0 &&
    industry.trim().length > 0 &&
    hasValidProcesses &&
    splitCommaSeparated(currentSkills).length > 0 &&
    !submitting;

  const updateProcess = (index: number, patch: Partial<ProcessDraft>) => {
    setProcesses((prev) =>
      prev.map((process, i) => (i === index ? { ...process, ...patch } : process))
    );
  };

  const addProcess = () => {
    setProcesses((prev) => [...prev, { name: "", description: "", activities: "" }]);
  };

  const removeProcess = (index: number) => {
    setProcesses((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      const response = await api.analyzeNewRole({
        name: name.trim(),
        industry: industry.trim(),
        description: description.trim() || null,
        processes: processes
          .filter((process) => process.name.trim().length > 0)
          .map((process) => ({
            name: process.name.trim(),
            description: process.description.trim() || null,
            activities: splitLines(process.activities),
          })),
        current_skills: splitCommaSeparated(currentSkills),
      });
      navigate(`/role-intelligence/${response.role.id}`);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err
          : new ApiError(0, "unknown_error", err instanceof Error ? err.message : "Analysis failed. Please try again."),
      );
      setSubmitting(false);
    }
  };

  if (role === null || !["owner", "admin", "analyst"].includes(role)) {
    return (
      <div className="animate-fade-up">
        <PageHeader
          eyebrow="Workspace"
          title="New Role Analysis"
          description="Analyze any role to build its AI intelligence profile."
        />
        <ForbiddenState
          title="New role analysis isn't available to your role"
          description="Only owner, admin, and analyst members can run role analyses. Contact an owner or admin to upgrade your access."
        />
      </div>
    );
  }

  return (
    <div className="animate-fade-up">
      <PageHeader
        eyebrow="Workspace"
        title="New Role Analysis"
        description="Enter any role with its real processes, activities, and skills, and the analysis engine will build a persisted intelligence profile for it."
      />

      <div className="max-w-2xl">
        <Card>
          <form onSubmit={handleSubmit} className="space-y-8">
            {/* ROLE CONTEXT */}
            <fieldset disabled={submitting}>
              <SectionHeading step="1">Role context</SectionHeading>
              <p className="mt-1 text-xs text-ink-muted">
                The role as it exists today. Richer context produces more accurate intelligence.
              </p>

              <div className="mt-5 space-y-4">
                <div>
                  <label htmlFor="role-name" className="label">
                    Role name <span className="text-danger-600">*</span>
                  </label>
                  <input
                    id="role-name"
                    type="text"
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    placeholder="e.g. Revenue Operations Manager"
                    required
                    maxLength={150}
                    className="input"
                  />
                </div>

                <div>
                  <label htmlFor="role-industry" className="label">
                    Industry <span className="text-danger-600">*</span>
                  </label>
                  <input
                    id="role-industry"
                    type="text"
                    value={industry}
                    onChange={(event) => setIndustry(event.target.value)}
                    placeholder="e.g. Technology / SaaS"
                    list="industry-suggestions"
                    required
                    maxLength={100}
                    className="input"
                  />
                  <datalist id="industry-suggestions">
                    {INDUSTRY_SUGGESTIONS.map((value) => (
                      <option key={value} value={value} />
                    ))}
                  </datalist>
                </div>

                <div>
                  <label htmlFor="role-description" className="label">
                    Description <span className="font-normal text-ink-muted">(optional)</span>
                  </label>
                  <textarea
                    id="role-description"
                    value={description}
                    onChange={(event) => setDescription(event.target.value)}
                    placeholder="What does this role do? Provides context for a more accurate analysis."
                    rows={3}
                    maxLength={2000}
                    className="textarea"
                  />
                </div>
              </div>
            </fieldset>

            {/* WORK CONTEXT */}
            <fieldset disabled={submitting}>
              <SectionHeading step="2">Work context</SectionHeading>
              <p className="mt-1 text-xs text-ink-muted">
                The processes, activities, and skills that make up the role's day-to-day work.
              </p>

              <div className="mt-5 space-y-4">
                <div className="space-y-3 rounded-xl border border-border-default bg-surface-sunken p-4">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold text-ink-primary">
                      Processes &amp; activities <span className="text-danger-600">*</span>
                    </p>
                    <button
                      type="button"
                      onClick={addProcess}
                      className="btn btn-secondary px-2 py-1 text-xs"
                    >
                      <Plus size={14} aria-hidden="true" />
                      Add process
                    </button>
                  </div>

                  {processes.map((process, index) => (
                    <div
                      key={index}
                      className="space-y-3 rounded-lg border border-border-default bg-surface-card p-3"
                    >
                      <div className="flex items-start gap-2">
                        <div className="flex-1">
                          <label
                            htmlFor={`process-name-${index}`}
                            className="label text-xs"
                          >
                            Process name
                          </label>
                          <input
                            id={`process-name-${index}`}
                            type="text"
                            value={process.name}
                            onChange={(event) => updateProcess(index, { name: event.target.value })}
                            placeholder="e.g. Demand Planning"
                            maxLength={150}
                            className="input"
                          />
                        </div>
                        {processes.length > 1 && (
                          <button
                            type="button"
                            onClick={() => removeProcess(index)}
                            aria-label={`Remove process ${index + 1}`}
                            className="btn btn-ghost mt-6 p-1.5 text-ink-muted hover:bg-danger-50 hover:text-danger-600"
                          >
                            <Trash2 size={16} aria-hidden="true" />
                          </button>
                        )}
                      </div>
                      <div>
                        <label
                          htmlFor={`process-desc-${index}`}
                          className="label text-xs"
                        >
                          Process description <span className="font-normal text-ink-muted">(optional)</span>
                        </label>
                        <input
                          id={`process-desc-${index}`}
                          type="text"
                          value={process.description}
                          onChange={(event) => updateProcess(index, { description: event.target.value })}
                          placeholder="e.g. Forecast and plan demand"
                          maxLength={2000}
                          className="input"
                        />
                      </div>
                      <div>
                        <label
                          htmlFor={`process-activities-${index}`}
                          className="label text-xs"
                        >
                          Activities <span className="text-danger-600">*</span>{" "}
                          <span className="font-normal text-ink-muted">(one per line)</span>
                        </label>
                        <textarea
                          id={`process-activities-${index}`}
                          value={process.activities}
                          onChange={(event) => updateProcess(index, { activities: event.target.value })}
                          placeholder={"Forecast Demand\nAnalyze Historical Demand\nIdentify Anomalies"}
                          rows={3}
                          maxLength={2000}
                          className="textarea"
                        />
                      </div>
                    </div>
                  ))}
                </div>

                <div>
                  <label htmlFor="role-current-skills" className="label">
                    Current skills <span className="text-danger-600">*</span>{" "}
                    <span className="font-normal text-ink-muted">(comma-separated)</span>
                  </label>
                  <input
                    id="role-current-skills"
                    type="text"
                    value={currentSkills}
                    onChange={(event) => setCurrentSkills(event.target.value)}
                    placeholder="e.g. Data Analysis, SQL, Stakeholder Management"
                    required
                    maxLength={2000}
                    className="input"
                  />
                  <p className="mt-1.5 flex items-start gap-1.5 text-xs text-ink-muted">
                    <Info size={13} className="mt-0.5 shrink-0" aria-hidden="true" />
                    The role's skills today. Skill gaps are computed against the future skills the
                    analysis identifies.
                  </p>
                </div>
              </div>
            </fieldset>

            {error && <ErrorState title="Analysis could not be completed" error={error} />}

            <div className="border-t border-border-faint pt-5">
              <button
                type="submit"
                disabled={!canSubmit}
                className="btn btn-primary w-full sm:w-auto sm:px-6 sm:py-2.5"
              >
                <Sparkles size={16} aria-hidden="true" />
                Analyze Role
              </button>
              <p className="mt-2 text-[11px] text-ink-muted">
                The role, processes, activities, and skills are created and analyzed through the real
                AI pipeline — no predefined list, no placeholders.
              </p>
            </div>

            {submitting && (
              <div>
                <AnalysisLoading />
              </div>
            )}
          </form>
        </Card>

        <div className="mt-4 flex items-start gap-2 rounded-lg bg-surface-sunken px-3 py-2.5 text-xs text-ink-muted">
          <BrainCircuit size={14} className="mt-0.5 shrink-0 text-brand-600" aria-hidden="true" />
          <p>
            The role, its processes, activities, skills, analysis, and execution records are all
            persisted. No API keys or provider details are stored in the browser.
          </p>
        </div>
      </div>
    </div>
  );
}
