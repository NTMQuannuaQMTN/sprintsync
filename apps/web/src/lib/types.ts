// ─── Core Domain Types ───────────────────────────────────────────────────────

// Matches the backend's ProfileOut — a 1:1 extension of Supabase's
// auth.users, keyed by the same id (auth.uid()).
export interface User {
  id: string
  github_username: string | null
  email: string | null
  name: string | null
  avatar_url: string | null
  bio: string | null
  created_at: string
}

export interface Repository {
  id: string
  github_repo_id: number
  full_name: string
  name: string
  description: string | null
  default_branch: string
  language: string | null
  stars: number
  private: boolean
  html_url: string
  webhook_active: boolean
  has_action_token: boolean
  health_score: number | null
  task_count: number | null
  done_count: number | null
  pending_suggestions: number | null
  recent_commit_sha: string | null
  recent_commit_message: string | null
  created_at: string
  updated_at: string
}

export interface GitHubRepoItem {
  id: number
  full_name: string
  name: string
  description: string | null
  language: string | null
  stargazers_count: number
  private: boolean
  html_url: string
  default_branch: string
  already_connected: boolean
}

export type TaskStatus = 'todo' | 'in_progress' | 'done' | 'blocked' | 'cancelled'
export type TaskPriority = 'low' | 'medium' | 'high' | 'critical'

export interface Task {
  id: string
  repository_id: string
  spec_id: string | null
  parent_id: string | null
  title: string
  description: string | null
  status: TaskStatus
  priority: TaskPriority
  order_index: number
  ai_tags: string[] | null
  subtasks: Task[]
  created_at: string
  updated_at: string
}

export type SpecStatus = 'pending' | 'processing' | 'done' | 'error'

// A task extracted by AI from a spec, not yet persisted — returned only by
// specsApi.upload() for human review. Shape mirrors the backend's TaskCreate.
export interface DraftTask {
  title: string
  description: string | null
  status: TaskStatus
  priority: TaskPriority
  ai_tags: string[] | null
}

export interface ProjectSpec {
  id: string
  repository_id: string
  filename: string
  file_size: number | null
  mime_type: string
  storage_url: string | null
  status: SpecStatus
  ai_summary: string | null
  task_count: number
  error_message: string | null
  created_at: string
  draft_tasks: DraftTask[]
}

export type SuggestionStatus = 'pending' | 'approved' | 'rejected'
export type SuggestionAction = 'status_change' | 'progress_update' | 'add_comment'

export interface Suggestion {
  id: string
  repository_id: string
  task_id: string | null
  commit_id: string | null
  status: SuggestionStatus
  action: SuggestionAction
  proposed_status: string | null
  explanation: string
  confidence_score: number
  evidence: {
    source?: 'llm' | 'heuristic'
    // LLM-path fields (services/ai_reasoning/reasoning.py's _finalize_llm)
    work_type?: string
    summary?: string
    // Heuristic-path fields (task_matching.py, via _analyze_with_heuristic)
    matched_keywords?: string[]
    matched_files?: string[]
    explicit_reference?: boolean
  } | null
  reviewed_at: string | null
  reviewer_note: string | null
  created_at: string
  task_title: string | null
  commit_sha: string | null
  commit_message: string | null
}

export interface BulkReviewResult {
  count: number
}

// Matches the backend's CommitSummary — the trimmed shape embedded in
// DashboardData.recent_commits.
export interface Commit {
  id: string
  sha: string
  short_sha: string
  message: string
  author_name: string
  author_avatar: string | null
  committed_at: string
  additions: number
  deletions: number
  html_url: string
}

export interface CommitFile {
  filename: string
  status: string
  additions: number
  deletions: number
  patch: string | null
}

// Matches the backend's CommitOut — the full record returned by
// GET /repositories/{id}/commits, including changed-files/diff data.
export interface CommitDetail extends Commit {
  repository_id: string
  author_email: string
  branch: string
  changed_files: number
  files_changed: CommitFile[] | null
  analyzed: boolean
}

export interface CommitAnalyzeResult {
  commits_processed: number
  suggestions_created: number
}

export interface ActivityItem {
  id: string
  event_type: string
  title: string
  description: string | null
  created_at: string
  repository_name: string | null
}

export interface DashboardStats {
  total_repos: number
  total_tasks: number
  completed_tasks: number
  pending_suggestions: number
  completion_rate: number
}

export interface DashboardData {
  stats: DashboardStats
  repositories: Repository[]
  pending_suggestions: Suggestion[]
  recent_commits: Commit[]
  recent_activity: ActivityItem[]
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

// ─── UI Helpers ───────────────────────────────────────────────────────────────

export const STATUS_LABELS: Record<TaskStatus, string> = {
  todo: 'To Do',
  in_progress: 'In Progress',
  done: 'Done',
  blocked: 'Blocked',
  cancelled: 'Cancelled',
}

export const PRIORITY_LABELS: Record<TaskPriority, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  critical: 'Critical',
}

// ─── V2: Integrations, Pull Requests, Summaries, Project Intelligence ─────────

export interface Integration {
  id: string
  integration_type: 'github' | 'notion' | 'jira' | 'linear' | 'clickup' | 'confluence' | 'gitlab'
  workspace_name: string | null
  active: boolean
  created_at: string
}

export interface PullRequest {
  id: string
  repository_id: string
  number: number
  title: string
  body: string | null
  author: string
  html_url: string
  branch: string
  base_branch: string
  state: 'open' | 'merged' | 'closed'
  merged: boolean
  additions: number
  deletions: number
  changed_files: number
  opened_at: string
  updated_at_github: string | null
  closed_at: string | null
  analyzed: boolean
}

export interface SummaryResult {
  summary: string
  source: 'llm' | 'heuristic'
}

export interface StaleTask {
  task_id: string
  title: string
  status: string
  last_updated_at: string
  days_since_update: number
}

export interface UnmatchedActivity {
  kind: 'commit' | 'pull_request'
  id: string
  identifier: string
  summary: string
  occurred_at: string
}

export interface LargeChange {
  kind: 'commit' | 'pull_request'
  id: string
  identifier: string
  summary: string
  lines_changed: number
  occurred_at: string
}

export interface ProjectIntelligence {
  stale_tasks: StaleTask[]
  unmatched_activity: UnmatchedActivity[]
  unusually_large_changes: LargeChange[]
}
