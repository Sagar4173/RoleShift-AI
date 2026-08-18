import type { ApiError } from "../services/api";

const FIELD_LABELS: Record<string, string> = {
  display_name: "Display name",
  email: "Email",
  password: "Password",
  name: "Name",
  industry: "Industry",
  description: "Description",
  current_skills: "Current skills",
  processes: "Processes",
  activities: "Activities",
  skills: "Skills",
  role: "Role",
};

export function fieldLabel(field: string): string {
  const segments = field.split(".").filter((segment) => !/^\d+$/.test(segment));
  if (segments.length === 0) return "Form";
  const joined = segments.join(".");
  const label = FIELD_LABELS[joined] ?? FIELD_LABELS[segments[segments.length - 1]];
  if (label) return label;
  return segments
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1).replace(/_/g, " "))
    .join(" · ");
}

export function describeApiError(error: ApiError | null | undefined): {
  message: string;
  details: string[];
} {
  if (!error) {
    return { message: "", details: [] };
  }
  if (error.status === 429) {
    const base = error.message || "Too many requests. Please wait a moment and try again.";
    const hint =
      error.retryAfter !== null && error.retryAfter > 0
        ? ` You can retry in about ${error.retryAfter} second${error.retryAfter === 1 ? "" : "s"}.`
        : "";
    return { message: base + hint, details: [] };
  }
  if (error.status === 403) {
    return {
      message: error.message || "This action requires Owner or Admin access.",
      details: [],
    };
  }
  if (error.status === 422) {
    return {
      message: error.message || "Some of the provided information is invalid.",
      details: error.errors.map((item) => `${fieldLabel(item.field)}: ${item.message}`),
    };
  }
  return {
    message: error.message || "Something went wrong. Please try again.",
    details: [],
  };
}

export function fieldErrorsFor(
  error: ApiError,
  mapping: Record<string, string>,
): Record<string, string> {
  const result: Record<string, string> = {};
  for (const item of error.errors) {
    const key = mapping[item.field];
    if (key) {
      result[key] = item.message;
    }
  }
  return result;
}
