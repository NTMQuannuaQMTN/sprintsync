'use client'

import { useQuery } from '@tanstack/react-query'
import { ArrowRight, GitBranch, Sparkles, CheckCircle2, TrendingUp, GitCommit } from 'lucide-react'
import Link from 'next/link'
import { formatRelativeTime } from '@/lib/utils'
import { dashboardApi } from '@/lib/api'
import { ConfidenceBadge } from '@/components/ui/ConfidenceBar'
import { SkeletonCard } from '@/components/ui/Skeleton'
import AppShell from '@/components/layout/AppShell'
import type { Repository } from '@/lib/types'

function RepoProgressBar({ repo }: { repo: Repository }) {
  const total = repo.task_count ?? 0
  const done = repo.done_count ?? 0
  const pct = total > 0 ? Math.round((done / total) * 100) : 0
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-emerald-500 rounded-full transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[10px] text-gray-400 tabular-nums w-8 text-right">{pct}%</span>
    </div>
  )
}

export default function DashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: dashboardApi.get,
    refetchInterval: 60_000,
  })

  const stats = data?.stats

  return (
    <AppShell headerTitle="Dashboard" pendingSuggestions={stats?.pending_suggestions}>
      <div className="p-6 space-y-6 max-w-6xl mx-auto fade-in">

        {/* Stats row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            {
              label: 'Repositories',
              value: stats?.total_repos ?? '—',
              icon: <GitBranch className="w-4 h-4" />,
              color: 'text-blue-600',
              bg: 'bg-blue-50',
            },
            {
              label: 'Total Tasks',
              value: stats?.total_tasks ?? '—',
              icon: <CheckCircle2 className="w-4 h-4" />,
              color: 'text-emerald-600',
              bg: 'bg-emerald-50',
            },
            {
              label: 'Completion Rate',
              value: stats ? `${stats.completion_rate}%` : '—',
              icon: <TrendingUp className="w-4 h-4" />,
              color: 'text-purple-600',
              bg: 'bg-purple-50',
            },
            {
              label: 'Pending Reviews',
              value: stats?.pending_suggestions ?? '—',
              icon: <Sparkles className="w-4 h-4" />,
              color: 'text-amber-600',
              bg: 'bg-amber-50',
            },
          ].map((stat) => (
            <div key={stat.label} className="bg-white border border-gray-100 rounded-xl p-5">
              <div className={`w-8 h-8 ${stat.bg} rounded-lg flex items-center justify-center ${stat.color} mb-3`}>
                {stat.icon}
              </div>
              <div className="text-2xl font-bold text-gray-900 tabular-nums">{stat.value}</div>
              <div className="text-xs text-gray-500 mt-0.5">{stat.label}</div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Repositories */}
          <div className="lg:col-span-2 bg-white border border-gray-100 rounded-xl">
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-50">
              <span className="text-sm font-semibold text-gray-900">Repositories</span>
              <Link href="/repositories" className="text-xs text-[#0F62FE] hover:underline flex items-center gap-1">
                View all <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
            <div className="divide-y divide-gray-50">
              {isLoading ? (
                <div className="p-5 space-y-3">
                  {[0, 1, 2].map((i) => <SkeletonCard key={i} />)}
                </div>
              ) : data?.repositories.length === 0 ? (
                <div className="py-12 text-center">
                  <GitBranch className="w-8 h-8 text-gray-200 mx-auto mb-3" />
                  <p className="text-sm text-gray-400">No repositories connected yet</p>
                  <Link
                    href="/repositories"
                    className="mt-3 inline-flex items-center gap-1 text-xs text-[#0F62FE] hover:underline"
                  >
                    Connect one <ArrowRight className="w-3 h-3" />
                  </Link>
                </div>
              ) : (
                data?.repositories.slice(0, 5).map((repo) => (
                  <Link key={repo.id} href={`/repositories/${repo.id}`} className="block px-5 py-4 hover:bg-gray-50 transition-colors">
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-gray-900 truncate">{repo.name}</span>
                          {repo.private && (
                            <span className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">Private</span>
                          )}
                        </div>
                        {repo.description && (
                          <p className="text-xs text-gray-500 mt-0.5 truncate">{repo.description}</p>
                        )}
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {(repo.pending_suggestions ?? 0) > 0 && (
                          <span className="inline-flex items-center gap-1 text-[10px] bg-amber-50 text-amber-700 px-1.5 py-0.5 rounded-full">
                            <Sparkles className="w-2.5 h-2.5" />
                            {repo.pending_suggestions}
                          </span>
                        )}
                        {repo.language && (
                          <span className="text-[10px] text-gray-400">{repo.language}</span>
                        )}
                      </div>
                    </div>
                    <RepoProgressBar repo={repo} />
                    <div className="flex items-center gap-3 mt-1.5">
                      <span className="text-[10px] text-gray-400">{repo.task_count ?? 0} tasks</span>
                      <span className="text-[10px] text-gray-400">·</span>
                      <span className="text-[10px] text-gray-400">{repo.done_count ?? 0} done</span>
                    </div>
                  </Link>
                ))
              )}
            </div>
          </div>

          {/* Right column */}
          <div className="space-y-5">
            {/* Pending Suggestions */}
            <div className="bg-white border border-gray-100 rounded-xl">
              <div className="flex items-center justify-between px-4 py-3 border-b border-gray-50">
                <span className="text-sm font-semibold text-gray-900">Pending Review</span>
                <Sparkles className="w-3.5 h-3.5 text-amber-500" />
              </div>
              <div className="divide-y divide-gray-50 max-h-56 overflow-y-auto">
                {isLoading ? (
                  <div className="p-4 space-y-2">
                    {[0, 1].map((i) => <SkeletonCard key={i} />)}
                  </div>
                ) : (data?.pending_suggestions?.length ?? 0) === 0 ? (
                  <div className="py-8 text-center">
                    <CheckCircle2 className="w-5 h-5 text-emerald-300 mx-auto mb-2" />
                    <p className="text-xs text-gray-400">No pending reviews</p>
                  </div>
                ) : (
                  data?.pending_suggestions.map((s) => (
                    <div key={s.id} className="px-4 py-3 hover:bg-gray-50 transition-colors">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-xs text-gray-700 line-clamp-2">{s.task_title || s.explanation}</p>
                        <ConfidenceBadge score={s.confidence_score} />
                      </div>
                      <p className="text-[10px] text-gray-400 mt-1 truncate">{s.explanation}</p>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Recent Commits */}
            <div className="bg-white border border-gray-100 rounded-xl">
              <div className="flex items-center justify-between px-4 py-3 border-b border-gray-50">
                <span className="text-sm font-semibold text-gray-900">Recent Commits</span>
                <GitCommit className="w-3.5 h-3.5 text-gray-400" />
              </div>
              <div className="divide-y divide-gray-50 max-h-56 overflow-y-auto">
                {isLoading ? (
                  <div className="p-4 space-y-2">
                    {[0, 1].map((i) => <SkeletonCard key={i} />)}
                  </div>
                ) : (data?.recent_commits?.length ?? 0) === 0 ? (
                  <div className="py-8 text-center">
                    <GitCommit className="w-5 h-5 text-gray-200 mx-auto mb-2" />
                    <p className="text-xs text-gray-400">No commits yet</p>
                  </div>
                ) : (
                  data?.recent_commits.map((c) => (
                    <a
                      key={c.id}
                      href={c.html_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block px-4 py-3 hover:bg-gray-50 transition-colors"
                    >
                      <div className="flex items-start gap-2">
                        {c.author_avatar && (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={c.author_avatar} alt="" className="w-5 h-5 rounded-full mt-0.5" />
                        )}
                        <div className="flex-1 min-w-0">
                          <p className="text-xs text-gray-700 truncate">{c.message}</p>
                          <div className="flex items-center gap-1.5 mt-0.5">
                            <code className="text-[10px] font-mono text-gray-400">{c.short_sha}</code>
                            <span className="text-[10px] text-gray-300">·</span>
                            <span className="text-[10px] text-gray-400">{formatRelativeTime(c.committed_at)}</span>
                          </div>
                        </div>
                      </div>
                    </a>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  )
}
