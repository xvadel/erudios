const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
    message?: string
  ) {
    super(message || detail);
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("erudios_token") : null;

  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const res = await fetch(`${API_BASE}/api/v1${path}`, { ...options, headers });

  if (!res.ok) {
    let detail = "Request failed";
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {}
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export async function login(username: string, password: string): Promise<AuthResponse> {
  return request<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export async function register(
  username: string,
  password: string
): Promise<AuthResponse> {
  return request<AuthResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export async function getMe(): Promise<User> {
  return request<User>("/auth/me");
}

export async function updateProfile(data: Partial<UserProfile>): Promise<User> {
  return request<User>("/auth/profile", { method: "PUT", body: JSON.stringify(data) });
}

// ── Topics ────────────────────────────────────────────────────────────────────

export async function getRootTopics(): Promise<Topic[]> {
  return request<Topic[]>("/topics");
}

export async function getTopic(slug: string): Promise<Topic> {
  return request<Topic>(`/topics/${slug}`);
}

export async function getTopicChildren(slug: string): Promise<Topic[]> {
  return request<Topic[]>(`/topics/${slug}/children`);
}

export async function getPrerequisites(slug: string): Promise<Dependency[]> {
  return request<Dependency[]>(`/topics/${slug}/prerequisites`);
}

export async function getWhatsNext(
  slug: string,
  completed?: string[]
): Promise<WhatsNextResponse> {
  const params = completed ? `?completed=${completed.join(",")}` : "";
  return request<WhatsNextResponse>(`/topics/${slug}/whats-next${params}`);
}

export async function getLearningPath(slug: string): Promise<Topic[]> {
  return request<Topic[]>(`/topics/${slug}/learning-path`);
}

export async function searchTopics(q: string): Promise<Topic[]> {
  return request<Topic[]>(`/topics/search?q=${encodeURIComponent(q)}`);
}

// ── Resources ─────────────────────────────────────────────────────────────────

export async function getResources(
  topicSlug: string,
  params?: { source_type?: string; min_score?: number }
): Promise<Resource[]> {
  const qs = new URLSearchParams(params as Record<string, string>).toString();
  return request<Resource[]>(`/resources/topics/${topicSlug}${qs ? `?${qs}` : ""}`);
}

export async function triggerDiscovery(topicSlug: string) {
  return request(`/resources/topics/${topicSlug}/discover`, { method: "POST" });
}

// ── Curriculum ────────────────────────────────────────────────────────────────

export async function createCurriculum(topicSlug: string): Promise<Curriculum> {
  return request<Curriculum>(`/curriculum/${topicSlug}`, { method: "POST" });
}

export async function getCurriculum(id: string): Promise<Curriculum> {
  return request<Curriculum>(`/curriculum/${id}`);
}

export async function listMyCurricula(): Promise<CurriculumSummary[]> {
  return request<CurriculumSummary[]>("/curriculum/me");
}

export async function deleteCurriculum(id: string): Promise<void> {
  return request<void>(`/curriculum/${id}`, { method: "DELETE" });
}

// ── Artifacts ─────────────────────────────────────────────────────────────────

export async function getArtifactShell(topicSlug: string): Promise<ArtifactShell> {
  return request<ArtifactShell>(`/artifacts/${topicSlug}/shell`);
}

export async function getSectionContent(
  topicSlug: string,
  sectionSlug: string,
  style?: string
): Promise<SectionContent> {
  const qs = style ? `?style=${encodeURIComponent(style)}` : "";
  return request<SectionContent>(`/artifacts/${topicSlug}/sections/${sectionSlug}${qs}`);
}

export async function getSectionQuiz(
  topicSlug: string,
  sectionSlug: string
): Promise<QuizData> {
  return request<QuizData>(`/artifacts/${topicSlug}/sections/${sectionSlug}/quiz`);
}

// ── Progress ──────────────────────────────────────────────────────────────────

export async function completeModule(
  moduleId: string,
  timeSpentMinutes?: number
): Promise<ModuleProgress> {
  return request<ModuleProgress>(`/progress/modules/${moduleId}/complete`, {
    method: "POST",
    body: JSON.stringify({ time_spent_minutes: timeSpentMinutes ?? 0 }),
  });
}

export async function submitQuizResult(
  moduleId: string,
  score: number,
  timeSpentMinutes?: number
): Promise<ModuleProgress> {
  return request<ModuleProgress>(`/progress/modules/${moduleId}/quiz-result`, {
    method: "POST",
    body: JSON.stringify({ score, time_spent_minutes: timeSpentMinutes ?? 0 }),
  });
}

export async function getCurriculumProgress(
  curriculumId: string
): Promise<CurriculumProgress> {
  return request<CurriculumProgress>(`/progress/curricula/${curriculumId}`);
}

// ── Health ────────────────────────────────────────────────────────────────────

export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

// ── Types ─────────────────────────────────────────────────────────────────────

export interface User {
  id: string;
  username: string;
  name: string;
  avatar_url: string | null;
  level: string;
  learning_style: string;
  goal: string;
}

export interface UserProfile {
  level?: string;
  learning_style?: string;
  goal?: string;
  name?: string;
}

export interface Topic {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  difficulty: string;
  estimated_hours: number;
  parent_slug: string | null;
  child_count: number;
}

export interface Dependency {
  topic: Topic;
  reason: string | null;
}

export interface WhatsNextResponse {
  completed_topic: string;
  next_steps: Array<{
    topic: Topic;
    reason: string | null;
    readiness: string;
  }>;
  message: string;
}

export interface Resource {
  id: string;
  title: string;
  url: string;
  source_type: string;
  author: string | null;
  published_at: string | null;
  trust_score: number;
  quality_score: number;
  composite_score: number;
}

export interface CurriculumModule {
  id: string;
  order_index: number;
  title: string;
  description: string | null;
  why_next: string | null;
  estimated_hours: number;
  difficulty: string;
  topic_slug: string;
  topic_name: string;
}

export interface Curriculum {
  id: string;
  topic_slug: string;
  topic_name: string;
  level: string;
  learning_style: string;
  goal: string;
  modules: CurriculumModule[];
  created_at: string;
}

export interface CurriculumSummary {
  id: string;
  topic_slug: string;
  topic_name: string;
  level: string;
  learning_style: string;
  goal: string;
  module_count: number;
  created_at: string;
}

export interface ArtifactSection {
  slug: string;
  title: string;
}

export interface ArtifactShell {
  topic_slug: string;
  overview: string;
  sections: ArtifactSection[];
}

export interface SectionContent {
  topic_slug: string;
  section_slug: string;
  content: string;
  has_overlay: boolean;
  degraded: boolean;
}

export interface QuizQuestion {
  question: string;
  options: string[];
  correct_index: number;
  explanation: string;
}

export interface QuizData {
  topic_slug: string;
  section_slug: string;
  questions: QuizQuestion[];
}

export interface ModuleProgress {
  module_id: string;
  topic_slug: string;
  mastery_score: number;
  quizzes_taken: number;
  avg_quiz_score: number;
  time_spent_minutes: number;
  sections_completed: number;
  last_reviewed: string | null;
}

export interface CurriculumProgress {
  curriculum_id: string;
  total_modules: number;
  completed_modules: number;
  completion_pct: number;
  progress: ModuleProgress[];
}

export interface HealthResponse {
  status: string;
  version: string;
  providers: Record<string, { status: string; daily_budget_remaining_pct?: number; note?: string }>;
  features: {
    resource_discovery: string;
    curriculum_generation: string;
    artifact_generation: string;
    rag_tutor: string;
  };
}

