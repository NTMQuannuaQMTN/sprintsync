'use client'

import { useParams } from 'next/navigation'
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  GitBranch, Star, ExternalLink, CheckSquare, Sparkles,
  GitCommit, Upload, ArrowRight, Lock, RefreshCw, KeyRound, Copy, Check, Loader2
} from 'lucide-react'
import Link from 'next/link'
import { reposApi, tasksApi, suggestionsApi, specsApi, commitsApi } from '@/lib/api'
import { SkeletonCard } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { ConfidenceBadge } from '@/components/ui/ConfidenceBar'
import AppShell from '@/components/layout/AppShell'
import type { Repository, Task } from '@/lib/types'

function ConnectionsCard({ repo, repoId }: { repo: Repository; repoId: string }) {
  const queryClient = useQueryClient()
  const [newToken, setNewToken] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const reinstallMutation = useMutation({
    mutationFn: () => reposApi.reinstallWebhook(repoId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['repo', repoId] }),
  })
  const generateTokenMutation = useMutation({
    mutationFn: () => reposApi.generateActionToken(repoId),
    onSuccess: (data) => {
      setNewToken(data.action_token)
      queryClient.invalidateQueries({ queryKey: ['repo', repoId] })
    },
  })
  const revokeTokenMutation = useMutation({
    mutationFn: () => reposApi.revokeActionToken(repoId),
    onSuccess: () => {
      setNewToken(null)
      queryClient.invalidateQueries({ queryKey: ['repo', repoId] })
    },
  })

  const copyToken = () => {
    if (!newToken) return
    navigator.clipboard.writeText(newToken)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="bg-white border border-gray-100 rounded-xl">
      <div className="px-4 py-3 border-b border-gray-50">
        <span className="text-sm font-semibold text-gray-900">Connections</span>
      </div>
      <div className="p-4 space-y-4">
        {/* GitHub webhook */}
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-700">GitHub webhook</p>
            <p className="text-[11px] text-gray-500 mt-0.5">
              {repo.webhook_active ? 'Active — pushes/PRs sync automatically' : 'Not active on GitHub'}
            </p>
          </div>
          {!repo.webhook_active && (
            <button
              onClick={() => reinstallMutation.mutate()}
              disabled={reinstallMutation.isPending}
              className="flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium text-[#0F62FE] hover:bg-blue-50 rounded-md disabled:opacity-50"
            >
              {reinstallMutation.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
              Install
            </button>
          )}
        </div>
        {reinstallMutation.isError && (
          <p className="text-[11px] text-rose-600">{(reinstallMutation.error as Error).message}</p>
        )}

        <div className="border-t border-gray-50 pt-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-gray-700">GitHub Action (no admin required)</p>
              <p className="text-[11px] text-gray-500 mt-0.5">
                {repo.has_action_token
                  ? 'A token exists — rotating issues a new one and invalidates the old.'
                  : 'Generate a token to use SprintSync from your own workflow instead of a webhook.'}
              </p>
            </div>
            <button
              onClick={() => generateTokenMutation.mutate()}
              disabled={generateTokenMutation.isPending}
              className="flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium text-[#0F62FE] hover:bg-blue-50 rounded-md disabled:opacity-50 flex-shrink-0"
            >
              {generateTokenMutation.isPending ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : (
                <KeyRound className="w-3 h-3" />
              )}
              {repo.has_action_token ? 'Rotate' : 'Generate'}
            </button>
          </div>

          {newToken && (
            <div className="mt-3 p-2.5 bg-amber-50 border border-amber-100 rounded-lg">
              <p className="text-[10px] text-amber-700 mb-1.5">
                Shown once — store it as your repo&apos;s <code>SPRINTSYNC_TOKEN</code> Actions secret now.
              </p>
              <div className="flex items-center gap-1.5">
                <code className="flex-1 text-[11px] font-mono bg-white border border-amber-200 rounded px-2 py-1 truncate">
                  {newToken}
                </code>
                <button onClick={copyToken} className="p-1.5 hover:bg-amber-100 rounded">
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5 text-amber-700" />}
                </button>
              </div>
            </div>
          )}

          {repo.has_action_token && (
            <button
              onClick={() => revokeTokenMutation.mutate()}
              disabled={revokeTokenMutation.isPending}
              className="mt-2 text-[11px] text-red-500 hover:text-red-700 font-medium disabled:opacity-50"
            >
              Revoke token
            </button>
          )}

          <p className="text-[10px] text-gray-400 mt-2">
            See docs/GITHUB_ACTION.md and docs/examples/sprintsync-sync.yml for the workflow setup.
          </p>
        </div>
      </div>
    </div>
  )
}

function ProgressRing({ pct }: { pct: number }) {
  const r = 20
  const circ = 2 * Math.PI * r
  const dash = (pct / 100) * circ
  return (
    <svg width="52" height="52" viewBox="0 0 52 52">
      <circle cx="26" cy="26" r={r} fill="none" stroke="#F3F4F6" strokeWidth="4" />
      <circle
        cx="26" cy="26" r={r} fill="none" stroke="#10B981" strokeWidth="4"
        strokeDasharray={`${dash} ${circ - dash}`}
        strokeLinecap="round"
        transform="rotate(-90 26 26)"
        className="transition-all duration-700"
      />
      <text x="26" y="31" textAnchor="middle" fontSize="11" fontWeight="600" fill="#111827">
        {pct}%
      </text>
    </svg>
  )
}

export default function RepositoryDetailPage() {
  const { id } = useParams<{ id: string }>()

  const { data: repo, isLoading: loadingRepo } = useQuery({
    queryKey: ['repo', id],
    queryFn: () => reposApi.get(id),
  })

  const { data: tasks, isLoading: loadingTasks } = useQuery({
    queryKey: ['tasks', id],
    queryFn: () => tasksApi.list(id),
    enabled: !!id,
  })

  const { data: suggestions } = useQuery({
    queryKey: ['suggestions', id, 'pending'],
    queryFn: () => suggestionsApi.list(id, 'pending'),
    enabled: !!id,
  })

  const { data: specs } = useQuery({
    queryKey: ['specs', id],
    queryFn: () => specsApi.list(id),
    enabled: !!id,
  })

  const { data: commits } = useQuery({
    queryKey: ['commits', id],
    queryFn: () => commitsApi.list(id, 3),
    enabled: !!id,
  })

  const total = tasks?.length ?? 0
  const done = tasks?.filter((t: Task) => t.status === 'done').length ?? 0
  const inProgress = tasks?.filter((t: Task) => t.status === 'in_progress').length ?? 0
  const pct = total > 0 ? Math.round((done / total) * 100) : 0
  const pendingSuggestions = suggestions?.length ?? 0

  return (
    <AppShell
      headerTitle={repo?.name}
      repoId={id}
      repoName={repo?.name}
      pendingSuggestions={pendingSuggestions}
    >
      <div className="p-6 max-w-5xl mx-auto space-y-6 fade-in">
        {loadingRepo ? (
          <SkeletonCard />
        ) : repo ? (
          <>
            {/* Repo header card */}
            <div className="bg-white border border-gray-100 rounded-xl p-6">
              <div className="flex items-start gap-6">
                <ProgressRing pct={pct} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h2 className="text-lg font-bold text-gray-900">{repo.name}</h2>
                    {repo.private && <Lock className="w-3.5 h-3.5 text-gray-400" />}
                    <a
                      href={repo.html_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-gray-300 hover:text-gray-600 transition-colors"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  </div>
                  <p className="text-sm text-gray-500 mb-3">{repo.full_name}</p>
                  {repo.description && (
                    <p className="text-sm text-gray-600 mb-3">{repo.description}</p>
                  )}
                  <div className="flex items-center gap-4 flex-wrap">
                    {repo.language && (
                      <span className="text-xs text-gray-500">{repo.language}</span>
                    )}
                    <span className="flex items-center gap-1 text-xs text-gray-500">
                      <Star className="w-3 h-3" /> {repo.stars}
                    </span>
                    <span className="text-xs text-gray-500">
                      Branch: <code className="font-mono">{repo.default_branch}</code>
                    </span>
                    <span className={`flex items-center gap-1 text-xs px-2 py-0.5 rounded-full ${repo.webhook_active ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-gray-500'}`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${repo.webhook_active ? 'bg-emerald-500 agent-pulse' : 'bg-gray-400'}`} />
                      Webhook {repo.webhook_active ? 'active' : 'inactive'}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Quick stats */}
            <div className="grid grid-cols-4 gap-4">
              {[
                { label: 'Total Tasks', value: total, color: 'text-gray-900' },
                { label: 'In Progress', value: inProgress, color: 'text-blue-700' },
                { label: 'Completed', value: done, color: 'text-emerald-700' },
                { label: 'AI Suggestions', value: pendingSuggestions, color: 'text-amber-700' },
              ].map((s) => (
                <div key={s.label} className="bg-white border border-gray-100 rounded-xl p-4 text-center">
                  <div className={`text-2xl font-bold tabular-nums ${s.color}`}>{s.value}</div>
                  <div className="text-xs text-gray-500 mt-0.5">{s.label}</div>
                </div>
              ))}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
              {/* Tasks preview */}
              <div className="lg:col-span-3 bg-white border border-gray-100 rounded-xl">
                <div className="flex items-center justify-between px-5 py-4 border-b border-gray-50">
                  <span className="text-sm font-semibold text-gray-900">Tasks</span>
                  <Link href={`/repositories/${id}/tasks`} className="text-xs text-[#0F62FE] hover:underline flex items-center gap-1">
                    View all <ArrowRight className="w-3 h-3" />
                  </Link>
                </div>
                {loadingTasks ? (
                  <div className="p-4 space-y-2">{[0, 1, 2].map((i) => <SkeletonCard key={i} />)}</div>
                ) : tasks?.length === 0 ? (
                  <div className="py-10 text-center">
                    <CheckSquare className="w-7 h-7 text-gray-200 mx-auto mb-2" />
                    <p className="text-sm text-gray-400">No tasks yet</p>
                    <Link href={`/repositories/${id}/upload`} className="mt-2 inline-flex items-center gap-1 text-xs text-[#0F62FE] hover:underline">
                      <Upload className="w-3 h-3" /> Upload a spec to generate tasks
                    </Link>
                  </div>
                ) : (
                  <div className="divide-y divide-gray-50">
                    {tasks?.slice(0, 6).map((task: Task) => (
                      <div key={task.id} className="px-5 py-3 flex items-start gap-3">
                        <StatusBadge status={task.status} />
                        <span className="flex-1 text-sm text-gray-700 truncate">{task.title}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Right column */}
              <div className="lg:col-span-2 space-y-5">
                {/* Upload spec */}
                <Link
                  href={`/repositories/${id}/upload`}
                  className="block bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-100 rounded-xl p-5 hover:border-blue-200 transition-colors"
                >
                  <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center mb-3">
                    <Upload className="w-4 h-4 text-blue-700" />
                  </div>
                  <h3 className="text-sm font-semibold text-gray-900 mb-1">Upload Specification</h3>
                  <p className="text-xs text-gray-500">
                    Upload a PDF or DOCX and AI will extract implementation tasks.
                  </p>
                  {specs && specs.length > 0 && (
                    <p className="text-xs text-blue-700 mt-2">{specs.length} spec{specs.length > 1 ? 's' : ''} uploaded</p>
                  )}
                </Link>

                {/* Pending suggestions */}
                {pendingSuggestions > 0 && (
                  <div className="bg-white border border-amber-100 rounded-xl">
                    <div className="flex items-center justify-between px-4 py-3 border-b border-amber-50">
                      <span className="text-sm font-semibold text-gray-900 flex items-center gap-2">
                        <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                        AI Suggestions
                      </span>
                      <Link href={`/repositories/${id}/suggestions`} className="text-xs text-[#0F62FE] hover:underline">
                        Review
                      </Link>
                    </div>
                    <div className="divide-y divide-amber-50">
                      {suggestions?.slice(0, 3).map((s) => (
                        <div key={s.id} className="px-4 py-3">
                          <div className="flex items-start gap-2">
                            <ConfidenceBadge score={s.confidence_score} />
                            <p className="text-xs text-gray-700 flex-1 truncate">{s.task_title || s.explanation}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Recent commits */}
                <div className="bg-white border border-gray-100 rounded-xl">
                  <div className="flex items-center justify-between px-4 py-3 border-b border-gray-50">
                    <span className="text-sm font-semibold text-gray-900 flex items-center gap-2">
                      <GitCommit className="w-3.5 h-3.5 text-gray-400" />
                      Recent Commits
                    </span>
                    <Link href={`/repositories/${id}/commits`} className="text-xs text-[#0F62FE] hover:underline">
                      View all
                    </Link>
                  </div>
                  {(commits?.length ?? 0) === 0 ? (
                    <p className="px-4 py-6 text-xs text-gray-400 text-center">No commits yet</p>
                  ) : (
                    <div className="divide-y divide-gray-50">
                      {commits?.map((c) => (
                        <div key={c.id} className="px-4 py-3">
                          <p className="text-xs text-gray-700 truncate">{c.message}</p>
                          <div className="flex items-center gap-1.5 mt-1">
                            <code className="text-[10px] font-mono text-gray-400">{c.short_sha}</code>
                            <span className="text-[10px] text-gray-300">·</span>
                            <span className="text-[10px] text-gray-400">{c.changed_files} file{c.changed_files === 1 ? '' : 's'}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <ConnectionsCard repo={repo} repoId={id} />
              </div>
            </div>
          </>
        ) : null}
      </div>
    </AppShell>
  )
}
