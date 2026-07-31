'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Plus, X, GitBranch, Star, Lock, Globe, Sparkles,
  ExternalLink, Loader2, CheckCircle2
} from 'lucide-react'
import Link from 'next/link'
import { reposApi } from '@/lib/api'
import { formatRelativeTime } from '@/lib/utils'
import AppShell from '@/components/layout/AppShell'
import EmptyState from '@/components/ui/EmptyState'
import { SkeletonCard } from '@/components/ui/Skeleton'
import type { GitHubRepoItem } from '@/lib/types'

function ConnectModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')

  const { data: ghRepos, isLoading } = useQuery({
    queryKey: ['github-repos'],
    queryFn: reposApi.listGitHub,
  })

  const connectMutation = useMutation({
    mutationFn: (id: number) => reposApi.connect(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['repositories'] })
      queryClient.invalidateQueries({ queryKey: ['github-repos'] })
    },
  })

  const filtered = (ghRepos ?? []).filter(
    (r) =>
      r.full_name.toLowerCase().includes(search.toLowerCase()) ||
      (r.description ?? '').toLowerCase().includes(search.toLowerCase()),
  )

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl w-full max-w-lg shadow-2xl fade-in overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div>
            <h2 className="text-base font-semibold text-gray-900">Connect Repository</h2>
            <p className="text-xs text-gray-500 mt-0.5">Select a GitHub repository to connect</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700 p-1 rounded-lg hover:bg-gray-100 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Search */}
        <div className="px-6 py-3 border-b border-gray-50">
          <input
            type="text"
            placeholder="Search repositories…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-[#0F62FE]/20 focus:border-[#0F62FE]"
            autoFocus
          />
        </div>

        {/* Repo list */}
        <div className="max-h-80 overflow-y-auto divide-y divide-gray-50">
          {isLoading ? (
            <div className="p-4 space-y-2">
              {[0, 1, 2].map((i) => <SkeletonCard key={i} />)}
            </div>
          ) : filtered.length === 0 ? (
            <div className="py-10 text-center text-sm text-gray-400">No repositories found</div>
          ) : (
            filtered.map((repo: GitHubRepoItem) => (
              <div key={repo.id} className="flex items-center gap-3 px-6 py-3 hover:bg-gray-50 transition-colors">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    {repo.private ? (
                      <Lock className="w-3 h-3 text-gray-400 flex-shrink-0" />
                    ) : (
                      <Globe className="w-3 h-3 text-gray-400 flex-shrink-0" />
                    )}
                    <span className="text-sm font-medium text-gray-900 truncate">{repo.full_name}</span>
                  </div>
                  {repo.description && (
                    <p className="text-xs text-gray-500 mt-0.5 truncate">{repo.description}</p>
                  )}
                  <div className="flex items-center gap-2 mt-1">
                    {repo.language && <span className="text-[10px] text-gray-400">{repo.language}</span>}
                    <span className="flex items-center gap-0.5 text-[10px] text-gray-400">
                      <Star className="w-2.5 h-2.5" />
                      {repo.stargazers_count}
                    </span>
                  </div>
                </div>
                {repo.already_connected ? (
                  <span className="flex items-center gap-1 text-xs text-emerald-600 font-medium flex-shrink-0">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Connected
                  </span>
                ) : (
                  <button
                    onClick={() => connectMutation.mutate(repo.id)}
                    disabled={connectMutation.isPending}
                    className="px-3 py-1.5 bg-[#0F62FE] text-white text-xs rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50 flex-shrink-0"
                  >
                    {connectMutation.isPending ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : (
                      'Connect'
                    )}
                  </button>
                )}
              </div>
            ))
          )}
        </div>

        <div className="px-6 py-4 bg-gray-50 border-t border-gray-100">
          <button onClick={onClose} className="text-sm text-gray-500 hover:text-gray-700">
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}

export default function RepositoriesPage() {
  const [showModal, setShowModal] = useState(false)

  const { data: repos, isLoading } = useQuery({
    queryKey: ['repositories'],
    queryFn: reposApi.list,
  })

  const headerActions = (
    <button
      onClick={() => setShowModal(true)}
      className="flex items-center gap-1.5 px-3 py-1.5 bg-[#0F62FE] text-white text-xs rounded-lg hover:bg-blue-700 transition-colors font-medium"
    >
      <Plus className="w-3.5 h-3.5" />
      Connect Repo
    </button>
  )

  return (
    <AppShell headerTitle="Repositories" headerActions={headerActions}>
      <div className="p-6 max-w-5xl mx-auto fade-in">
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[0, 1, 2, 3].map((i) => <SkeletonCard key={i} />)}
          </div>
        ) : repos?.length === 0 ? (
          <EmptyState
            icon={GitBranch}
            title="No repositories connected"
            description="Connect a GitHub repository to start tracking tasks and commits."
            action={
              <button
                onClick={() => setShowModal(true)}
                className="inline-flex items-center gap-2 px-4 py-2 bg-[#0F62FE] text-white text-sm rounded-lg hover:bg-blue-700 transition-colors font-medium"
              >
                <Plus className="w-4 h-4" />
                Connect Repository
              </button>
            }
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {repos?.map((repo) => {
              const total = repo.task_count ?? 0
              const done = repo.done_count ?? 0
              const pct = total > 0 ? Math.round((done / total) * 100) : 0

              return (
                <Link
                  key={repo.id}
                  href={`/repositories/${repo.id}`}
                  className="bg-white border border-gray-100 rounded-xl p-5 hover:border-gray-200 hover:shadow-sm transition-all"
                >
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-gray-900 truncate">{repo.name}</h3>
                        {repo.private && (
                          <Lock className="w-3 h-3 text-gray-400 flex-shrink-0" />
                        )}
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5 truncate">{repo.full_name}</p>
                      {repo.description && (
                        <p className="text-xs text-gray-500 mt-1 line-clamp-2">{repo.description}</p>
                      )}
                    </div>
                    <a
                      href={repo.html_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="text-gray-300 hover:text-gray-600 transition-colors flex-shrink-0"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  </div>

                  {/* Progress */}
                  <div className="mb-3">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10px] text-gray-400">Progress</span>
                      <span className="text-[10px] text-gray-500 tabular-nums">{done}/{total}</span>
                    </div>
                    <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-emerald-500 rounded-full transition-all"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>

                  {/* Meta */}
                  <div className="flex items-center gap-3 flex-wrap">
                    {repo.language && (
                      <span className="text-[10px] text-gray-400">{repo.language}</span>
                    )}
                    <span className="flex items-center gap-0.5 text-[10px] text-gray-400">
                      <Star className="w-2.5 h-2.5" />
                      {repo.stars}
                    </span>
                    {(repo.pending_suggestions ?? 0) > 0 && (
                      <span className="flex items-center gap-1 text-[10px] bg-amber-50 text-amber-700 px-1.5 py-0.5 rounded-full">
                        <Sparkles className="w-2.5 h-2.5" />
                        {repo.pending_suggestions} suggestions
                      </span>
                    )}
                    <span className={`flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-full ${repo.webhook_active ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-gray-500'}`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${repo.webhook_active ? 'bg-emerald-500' : 'bg-gray-400'}`} />
                      Webhook {repo.webhook_active ? 'active' : 'inactive'}
                    </span>
                  </div>
                </Link>
              )
            })}
          </div>
        )}
      </div>

      {showModal && <ConnectModal onClose={() => setShowModal(false)} />}
    </AppShell>
  )
}
