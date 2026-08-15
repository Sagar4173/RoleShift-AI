export type RoleStatus = "active" | "inactive";
export type HumanInvolvement = "full" | "partial" | "none";
export type ImpactLevel = "none" | "low" | "medium" | "high";
export type ReskillingPriority = "low" | "medium" | "high" | "critical";

export interface PageMeta {
  skip: number;
  limit: number;
  total: number;
}

export interface Page<T> {
  items: T[];
  meta: PageMeta;
}

export interface Organization {
  id: string;
  name: string;
  industry: string | null;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface OrganizationCreate {
  name: string;
  industry?: string | null;
  description?: string | null;
}

export interface Role {
  id: string;
  organization_id: string;
  name: string;
  description: string | null;
  industry: string | null;
  status: RoleStatus;
  created_at: string;
  updated_at: string;
}

export interface RoleListItem extends Role {
  has_analysis: boolean;
  ai_exposure_score: number | null;
  ai_exposure_level: ImpactLevel | null;
  reskilling_priority: ReskillingPriority | null;
}

export interface RoleCreate {
  organization_id: string;
  name: string;
  description?: string | null;
  industry?: string | null;
  status?: RoleStatus;
}

export interface Process {
  id: string;
  organization_id: string;
  name: string;
  description: string | null;
  industry: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProcessCreate {
  organization_id: string;
  name: string;
  description?: string | null;
  industry?: string | null;
}

export interface Activity {
  id: string;
  process_id: string;
  role_id: string;
  name: string;
  description: string | null;
  sequence: number;
  current_human_involvement: HumanInvolvement;
  created_at: string;
  updated_at: string;
}

export interface ActivityCreate {
  process_id: string;
  role_id: string;
  name: string;
  description?: string | null;
  sequence?: number;
  current_human_involvement?: HumanInvolvement;
}

export interface Skill {
  id: string;
  name: string;
  description: string | null;
  category: string | null;
  created_at: string;
  updated_at: string;
}

export interface SkillCreate {
  name: string;
  description?: string | null;
  category?: string | null;
}

export interface AiExposureSummary {
  score: number;
  level: ImpactLevel;
  summary: string;
}

export interface ActivityImpact {
  activity_id: string;
  activity_name: string;
  impact_level: ImpactLevel;
  automation_score: number;
  augmentation_score: number;
  human_responsibility: string | null;
  description: string | null;
}

export interface FutureResponsibility {
  title: string;
  description: string | null;
  rationale: string | null;
}

export interface CurrentSkill {
  name: string;
  category: string | null;
}

export interface SkillGap {
  skill_name: string;
  category: string | null;
  relevance: number;
  priority: ReskillingPriority;
  reason: string;
}

export interface FutureSkill {
  name: string;
  category: string | null;
  relevance: number;
  priority: ReskillingPriority;
}

export interface Recommendation {
  title: string;
  description: string | null;
  rationale: string | null;
  priority: ReskillingPriority;
}

export interface ModelMetadata {
  provider: string;
  model: string | null;
  model_version: string | null;
  prompt_version: string | null;
}

export interface RoleAnalysis {
  id: string;
  role_id: string;
  analysis_version: string;
  ai_exposure: AiExposureSummary;
  automation_score: number;
  augmentation_score: number;
  reskilling_priority: ReskillingPriority;
  activity_impacts: ActivityImpact[];
  future_responsibilities: FutureResponsibility[];
  future_skills: FutureSkill[];
  skill_gaps: SkillGap[];
  current_skills: CurrentSkill[];
  recommendations: Recommendation[];
  reasoning: string | null;
  model_metadata: ModelMetadata | null;
  created_at: string;
  updated_at: string;
}

export interface AnalysisStatus {
  role_id: string;
  has_analysis: boolean;
  latest: RoleAnalysis | null;
}

export interface AnalyzeProcessInput {
  name: string;
  description?: string | null;
  activities: string[];
}

export interface AnalyzeNewRequest {
  name: string;
  industry?: string | null;
  description?: string | null;
  processes: AnalyzeProcessInput[];
  current_skills: string[];
}

export interface RoleCurrentSkillsUpdate {
  skills: string[];
}

export interface AnalyzeNewResponse {
  role: Role;
  analysis: RoleAnalysis;
}

export interface RoleCompareItem {
  role: Role;
  has_analysis: boolean;
  analysis: RoleAnalysis | null;
}

export interface RoleCompareResponse {
  roles: RoleCompareItem[];
}

export interface ImpactDistributionItem {
  level: ImpactLevel;
  count: number;
}

export interface FutureSkillAggregateItem {
  name: string;
  category: string | null;
  relevance: number;
  priority: ReskillingPriority;
  roles: number;
}

export interface RecentRoleAnalysisItem {
  role_id: string;
  role_name: string;
  industry: string | null;
  ai_exposure_score: number;
  ai_exposure_level: ImpactLevel;
  automation_score: number;
  augmentation_score: number;
  reskilling_priority: ReskillingPriority;
  analyzed_at: string;
  activity_count: number;
  future_skills_count: number;
}

export interface DashboardSummary {
  total_roles: number;
  roles_analyzed: number;
  high_ai_impact_roles: number;
  high_automation_activities: number;
  high_reskilling_priority_roles: number;
  top_future_skills: FutureSkillAggregateItem[];
  ai_impact_distribution: ImpactDistributionItem[];
  recent_role_analyses: RecentRoleAnalysisItem[];
}

export interface SkillRoleRef {
  role_id: string;
  role_name: string;
}

export interface SkillDemandItem {
  name: string;
  category: string | null;
  relevance: number;
  priority: ReskillingPriority;
  roles: SkillRoleRef[];
}

export interface SkillsSummary {
  items: SkillDemandItem[];
}

export interface ErrorDetail {
  code: string;
  message: string;
}

export interface ErrorResponse {
  detail: ErrorDetail;
}