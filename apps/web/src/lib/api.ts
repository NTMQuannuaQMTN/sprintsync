/**
 * Typed API client — wraps fetch with auth token injection.
 * All requests go through Next.js rewrites → FastAPI at /api/v1/*
 */
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
} from './types'

const BASE = '/api/v1'

// ─── Token Management ─────────────────────────────────────────────────────────

const TOKEN_KEY = 'sprintsync_token'

export function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

// ─── HTTP Helper ──────────────────────────────────────────────────────────────

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${BASE}${path}`, { ...options, headers })

  if (res.status === 401) {
    clearToken()
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
  loginUrl: () => `${BASE}/auth/login`,
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
    const token = getToken()
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
}
