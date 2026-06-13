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

  return res.json() as Promise<T>;
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export function getGoogleOAuthUrl() {
  return `${API_BASE}/api/v1/auth/google`;
}

export function getGitHubOAuthUrl() {
  return `${API_BASE}/api/v1/auth/github`;
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

// ── Health ────────────────────────────────────────────────────────────────────

export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

// ── Types ─────────────────────────────────────────────────────────────────────

export interface User {
  id: string;
  email: string;
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
