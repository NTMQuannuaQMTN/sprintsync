/**
 * Typed API client — wraps fetch with auth token injection.
 * All requests go through Next.js rewrites → FastAPI at /api/v1/*
 *
 * Authentication itself is owned by Supabase Auth (see lib/supabase.ts) —
 * this module just attaches the current Supabase session's access token to
 * every request as a Bearer token; the backend verifies it directly
 * against Supabase's JWT secret (see apps/api/src/core/security.py).
 */
import { supabase } from './supabase'
import type {
  User,
  Repository,
  GitHubRepoItem,
  Task,
  ProjectSpec,
  Suggestion,
  DashboardData,
  ActivityItem,
  CommitDetail,
  CommitAnalyzeResult,
  BulkReviewResult,
} from './types'

const BASE = '/api/v1'

async function getAccessToken(): Promise<string | null> {
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token ?? null
}

// ─── HTTP Helper ──────────────────────────────────────────────────────────────

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = await getAccessToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${BASE}${path}`, { ...options, headers })

  if (res.status === 401) {
    await supabase.auth.signOut()
    if (typeof window !== 'undefined') window.location.href = '/login'
    throw new Error('Unauthorized')
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(body.detail || 'Request failed')
  }

  if (res.status === 204) return undefined as T
  return res.json()
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export const authApi = {
  getMe: () => request<User>('/auth/me'),
  /** Call once right after supabase.auth.signInWithOAuth() resolves, with
   * session.provider_token — the backend has no other way to get a GitHub
   * API token, since Supabase doesn't persist/refresh it for us. */
  syncProviderToken: (providerToken: string) =>
    request<User>('/auth/sync', {
      method: 'POST',
      body: JSON.stringify({ provider_token: providerToken }),
    }),
  /** Post-signup onboarding: GitHub accounts often have no public display
   * name, so the auth.users -> profiles trigger leaves `name` null. */
  updateName: (name: string) =>
    request<User>('/auth/me', {
      method: 'PATCH',
      body: JSON.stringify({ name }),
    }),
}

// ─── Dashboard ────────────────────────────────────────────────────────────────

export const dashboardApi = {
  get: () => request<DashboardData>('/dashboard'),
}

// ─── Repositories ─────────────────────────────────────────────────────────────

export const reposApi = {
  list: () => request<Repository[]>('/repositories'),
  get: (id: string) => request<Repository>(`/repositories/${id}`),
  listGitHub: () => request<GitHubRepoItem[]>('/repositories/github/available'),
  connect: (githubRepoId: number) =>
    request<Repository>(`/repositories?github_repo_id=${githubRepoId}`, { method: 'POST' }),
  disconnect: (id: string) => request<void>(`/repositories/${id}`, { method: 'DELETE' }),
}

// ─── Tasks ────────────────────────────────────────────────────────────────────

export const tasksApi = {
  list: (repoId: string, status?: string) =>
    request<Task[]>(`/repositories/${repoId}/tasks${status ? `?status=${status}` : ''}`),
  get: (repoId: string, taskId: string) =>
    request<Task>(`/repositories/${repoId}/tasks/${taskId}`),
  create: (repoId: string, data: Partial<Task>) =>
    request<Task>(`/repositories/${repoId}/tasks`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  bulkCreate: (repoId: string, tasks: Partial<Task>[], specId?: string) =>
    request<Task[]>(`/repositories/${repoId}/tasks/bulk`, {
      method: 'POST',
      body: JSON.stringify({ tasks, spec_id: specId }),
    }),
  update: (repoId: string, taskId: string, data: Partial<Task>) =>
    request<Task>(`/repositories/${repoId}/tasks/${taskId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  delete: (repoId: string, taskId: string) =>
    request<void>(`/repositories/${repoId}/tasks/${taskId}`, { method: 'DELETE' }),
}

// ─── Project Specs ────────────────────────────────────────────────────────────

export const specsApi = {
  list: (repoId: string) => request<ProjectSpec[]>(`/repositories/${repoId}/specs`),
  upload: async (repoId: string, file: File): Promise<ProjectSpec> => {
    const token = await getAccessToken()
    const formData = new FormData()
    formData.append('file', file)
    const res = await fetch(`${BASE}/repositories/${repoId}/specs`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    })
    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(body.detail || 'Upload failed')
    }
    return res.json()
  },
  getTasks: (repoId: string, specId: string) =>
    request<Task[]>(`/repositories/${repoId}/specs/${specId}/tasks`),
}

// ─── Suggestions ──────────────────────────────────────────────────────────────

export const suggestionsApi = {
  list: (repoId: string, status?: string) =>
    request<Suggestion[]>(`/repositories/${repoId}/suggestions${status ? `?status=${status}` : ''}`),
  get: (repoId: string, id: string) =>
    request<Suggestion>(`/repositories/${repoId}/suggestions/${id}`),
  approve: (repoId: string, id: string, note?: string) =>
    request<Suggestion>(`/repositories/${repoId}/suggestions/${id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ note }),
    }),
  reject: (repoId: string, id: string, note?: string) =>
    request<Suggestion>(`/repositories/${repoId}/suggestions/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify({ note }),
    }),
  approveAll: (repoId: string) =>
    request<BulkReviewResult>(`/repositories/${repoId}/suggestions/approve-all`, {
      method: 'POST',
      body: JSON.stringify({}),
    }),
  rejectAll: (repoId: string) =>
    request<BulkReviewResult>(`/repositories/${repoId}/suggestions/reject-all`, {
      method: 'POST',
      body: JSON.stringify({}),
    }),
}

// ─── Activity ─────────────────────────────────────────────────────────────────

export const activityApi = {
  list: (repoId: string, limit = 50) =>
    request<ActivityItem[]>(`/repositories/${repoId}/activity?limit=${limit}`),
}

// ─── Commits ──────────────────────────────────────────────────────────────────

export const commitsApi = {
  list: (repoId: string, limit = 30) =>
    request<CommitDetail[]>(`/repositories/${repoId}/commits?limit=${limit}`),
  get: (repoId: string, commitId: string) =>
    request<CommitDetail>(`/repositories/${repoId}/commits/${commitId}`),
  analyze: (repoId: string) =>
    request<CommitAnalyzeResult>(`/repositories/${repoId}/commits/analyze`, { method: 'POST' }),
}
