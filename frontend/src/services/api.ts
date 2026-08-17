import type {
  Activity,
  ActivityCreate,
  AnalysisStatus,
  AnalyzeNewRequest,
  AnalyzeNewResponse,
  AuthUser,
  DashboardSummary,
  LoginRequest,
  Organization,
  OrganizationCreate,
  Page,
  Process,
  ProcessCreate,
  RegisterRequest,
  Role,
  RoleAnalysis,
  RoleCompareResponse,
  RoleCreate,
  RoleCurrentSkillsUpdate,
  RoleListItem,
  Skill,
  SkillCreate,
  SkillsSummary,
} from "../types/api";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "/api/v1").replace(/\/$/, "");

let unauthorizedHandler: (() => void) | null = null;

/** Register a callback invoked when the API returns 401 (expired/invalid session). */
export function onUnauthorized(handler: (() => void) | null): void {
  unauthorizedHandler = handler;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      ...init,
    });
  } catch {
    throw new ApiError(0, "network_error", "Unable to reach the API server");
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const body = (await response.json().catch(() => null)) as
    | { detail?: { code?: string; message?: string } }
    | null;

  if (!response.ok) {
    if (response.status === 401 && unauthorizedHandler) {
      unauthorizedHandler();
    }
    throw new ApiError(
      response.status,
      body?.detail?.code ?? "request_failed",
      body?.detail?.message ?? `Request failed with status ${response.status}`,
    );
  }

  return body as T;
}

function toQuery(params: Record<string, string | number | undefined>): string {
  const entries = Object.entries(params).filter(
    (entry): entry is [string, string | number] => entry[1] !== undefined,
  );
  const query = new URLSearchParams(entries.map(([key, value]) => [key, String(value)]));
  const text = query.toString();
  return text ? `?${text}` : "";
}

const MAX_LIMIT = 100;

function clampLimit(limit?: number): number | undefined {
  return limit === undefined ? undefined : Math.max(1, Math.min(MAX_LIMIT, limit));
}

export const api = {
  // Authentication
  getCurrentUser(): Promise<AuthUser> {
    return request("/auth/me");
  },
  login(payload: LoginRequest): Promise<AuthUser> {
    return request("/auth/login", { method: "POST", body: JSON.stringify(payload) });
  },
  register(payload: RegisterRequest): Promise<AuthUser> {
    return request("/auth/register", { method: "POST", body: JSON.stringify(payload) });
  },
  logout(): Promise<void> {
    return request("/auth/logout", { method: "POST" });
  },

  // Organizations
  listOrganizations(skip = 0, limit = 50): Promise<Page<Organization>> {
    return request(`/organizations${toQuery({ skip, limit })}`);
  },
  getOrganization(id: string): Promise<Organization> {
    return request(`/organizations/${id}`);
  },
  createOrganization(payload: OrganizationCreate): Promise<Organization> {
    return request("/organizations", { method: "POST", body: JSON.stringify(payload) });
  },

  // Roles
  listRoles(
    options: {
      skip?: number;
      limit?: number;
      organizationId?: string;
      search?: string;
      industry?: string;
    } = {},
  ): Promise<Page<RoleListItem>> {
    return request(
      `/roles${toQuery({
        skip: options.skip,
        limit: clampLimit(options.limit),
        organization_id: options.organizationId,
        search: options.search,
        industry: options.industry,
      })}`,
    );
  },
  getRole(id: string): Promise<Role> {
    return request(`/roles/${id}`);
  },
  createRole(payload: RoleCreate): Promise<Role> {
    return request("/roles", { method: "POST", body: JSON.stringify(payload) });
  },
  deleteRole(id: string): Promise<void> {
    return request(`/roles/${id}`, { method: "DELETE" });
  },
  setRoleCurrentSkills(id: string, payload: RoleCurrentSkillsUpdate): Promise<Role> {
    return request(`/roles/${id}/current-skills`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },
  compareRoles(roleIds: string[]): Promise<RoleCompareResponse> {
    const query = roleIds.map((id) => `role_ids=${encodeURIComponent(id)}`).join("&");
    return request(`/roles/compare${query ? `?${query}` : ""}`);
  },
  analyzeNewRole(payload: AnalyzeNewRequest): Promise<AnalyzeNewResponse> {
    return request("/roles/analyze-new", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  // Processes
  listProcesses(skip = 0, limit = 50, organizationId?: string): Promise<Page<Process>> {
    return request(`/processes${toQuery({ skip, limit, organization_id: organizationId })}`);
  },
  createProcess(payload: ProcessCreate): Promise<Process> {
    return request("/processes", { method: "POST", body: JSON.stringify(payload) });
  },

  // Activities
  listActivities(skip = 0, limit = 50, roleId?: string, processId?: string): Promise<Page<Activity>> {
    return request(
      `/activities${toQuery({ skip, limit: clampLimit(limit), role_id: roleId, process_id: processId })}`,
    );
  },
  createActivity(payload: ActivityCreate): Promise<Activity> {
    return request("/activities", { method: "POST", body: JSON.stringify(payload) });
  },

  // Skills
  listSkills(skip = 0, limit = 50, category?: string): Promise<Page<Skill>> {
    return request(`/skills${toQuery({ skip, limit: clampLimit(limit), category })}`);
  },
  createSkill(payload: SkillCreate): Promise<Skill> {
    return request("/skills", { method: "POST", body: JSON.stringify(payload) });
  },

  // Analysis
  getRoleAnalysis(roleId: string): Promise<AnalysisStatus> {
    return request<AnalysisStatus>(`/roles/${roleId}/analysis`);
  },
  getRoleAnalysisLatest(roleId: string): Promise<RoleAnalysis | null> {
    return request<AnalysisStatus>(`/roles/${roleId}/analysis`).then((status) => status.latest);
  },
  analyzeRole(roleId: string, force = false): Promise<RoleAnalysis> {
    return request(`/roles/${roleId}/analyze`, {
      method: "POST",
      body: JSON.stringify({ force }),
    });
  },

  // Dashboard / analytics
  getDashboardSummary(): Promise<DashboardSummary> {
    return request("/dashboard/summary");
  },
  getSkillsSummary(): Promise<SkillsSummary> {
    return request("/dashboard/skills");
  },
};