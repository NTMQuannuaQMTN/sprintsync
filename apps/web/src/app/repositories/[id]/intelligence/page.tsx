'use client'

import { useState } from 'react'
import { useParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { Radar, Clock, GitCommit, GitPullRequest, TrendingUp, Sparkles } from 'lucide-react'
import { reposApi, intelligenceApi, summaryApi } from '@/lib/api'
import { SkeletonRow } from '@/components/ui/Skeleton'
import EmptyState from '@/components/ui/EmptyState'
import AppShell from '@/components/layout/AppShell'
import { formatRelativeTime } from '@/lib/utils'

function Section({
  title,
  icon: Icon,
  count,
  children,
  emptyLabel,
}: {
  title: string
  icon: typeof Radar
  count: number
  children: React.ReactNode
  emptyLabel: string
}) {
  return (
    <div className="bg-white border border-gray-100 rounded-xl">
      <div className="flex items-center gap-2 px-5 py-4 border-b border-gray-50">
        <Icon className="w-4 h-4 text-gray-400" />
        <span className="text-sm font-semibold text-gray-900">{title}</span>
        <span className="text-xs text-gray-400">({count})</span>
      </div>
      {count === 0 ? (
        <p className="px-5 py-6 text-xs text-gray-400 text-center">{emptyLabel}</p>
      ) : (
        <div className="divide-y divide-gray-50">{children}</div>
      )}
    </div>
  )
}

export default function RepoIntelligencePage() {
  const { id } = useParams<{ id: string }>()
  const [period, setPeriod] = useState<'day' | 'week'>('day')

  const { data: repo } = useQuery({
    queryKey: ['repo', id],
    queryFn: () => reposApi.get(id),
    enabled: !!id,
  })

  const { data: intel, isLoading } = useQuery({
    queryKey: ['intelligence', id],
    queryFn: () => intelligenceApi.get(id),
    enabled: !!id,
  })

  const { data: digest } = useQuery({
    queryKey: ['summary', id, period],
    queryFn: () => summaryApi.get(id, period),
    enabled: !!id,
  })

  return (
    <AppShell headerTitle="Project Intelligence" repoId={id} repoName={repo?.name}>
      <div className="p-6 max-w-3xl mx-auto fade-in space-y-6">
        <p className="text-xs text-gray-400 -mt-2">
          Observed facts derived directly from your data — not AI judgment about intent. See
          Suggestions for AI-inferred task matches.
        </p>

        {/* Digest */}
        <div className="bg-white border border-gray-100 rounded-xl p-5">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-violet-500" />
              <span className="text-sm font-semibold text-gray-900">Activity digest</span>
            </div>
            <div className="flex items-center gap-1 bg-gray-50 rounded-lg p-0.5">
              {(['day', 'week'] as const).map((p) => (
                <button
                  key={p}
                  onClick={() => setPeriod(p)}
                  className={`px-2.5 py-1 text-[11px] font-medium rounded-md transition-colors ${
                    period === p ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'
                  }`}
                >
                  {p === 'day' ? 'Today' : 'This week'}
                </button>
              ))}
            </div>
          </div>
          <p className="text-sm text-gray-700">{digest?.summary ?? '…'}</p>
          {digest && (
            <p className="text-[10px] text-gray-400 mt-1.5">
              {digest.source === 'llm' ? 'AI-generated' : 'Computed directly from repository data'}
            </p>
          )}
        </div>

        {isLoading ? (
          <div className="space-y-2">{[0, 1, 2].map((i) => <SkeletonRow key={i} />)}</div>
        ) : !intel ? (
          <EmptyState icon={Radar} title="No data yet" description="Connect activity to this repository first." />
        ) : (
          <>
            <Section
              title="Stale tasks"
              icon={Clock}
              count={intel.stale_tasks.length}
              emptyLabel="No open task has gone quiet for 14+ days."
            >
              {intel.stale_tasks.map((t) => (
                <div key={t.task_id} className="px-5 py-3 flex items-center justify-between gap-3">
                  <span className="text-sm text-gray-700 truncate">{t.title}</span>
                  <span className="text-[11px] text-amber-600 flex-shrink-0">
                    {t.days_since_update}d since last update
                  </span>
                </div>
              ))}
            </Section>

            <Section
              title="Unmatched activity"
              icon={GitCommit}
              count={intel.unmatched_activity.length}
              emptyLabel="Every analyzed commit/PR matched at least one task."
            >
              {intel.unmatched_activity.map((a) => (
                <div key={`${a.kind}-${a.id}`} className="px-5 py-3">
                  <div className="flex items-center gap-2">
                    {a.kind === 'pull_request' ? (
                      <GitPullRequest className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                    ) : (
                      <GitCommit className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                    )}
                    <code className="text-[10px] font-mono text-gray-400">{a.identifier}</code>
                    <span className="text-xs text-gray-700 truncate flex-1">{a.summary}</span>
                  </div>
                  <p className="text-[10px] text-gray-400 mt-1 ml-5">{formatRelativeTime(a.occurred_at)}</p>
                </div>
              ))}
            </Section>

            <Section
              title="Unusually large changes"
              icon={TrendingUp}
              count={intel.unusually_large_changes.length}
              emptyLabel="Nothing recently is a size outlier for this repository."
            >
              {intel.unusually_large_changes.map((c) => (
                <div key={`${c.kind}-${c.id}`} className="px-5 py-3">
                  <div className="flex items-center gap-2">
                    {c.kind === 'pull_request' ? (
                      <GitPullRequest className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                    ) : (
                      <GitCommit className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                    )}
                    <code className="text-[10px] font-mono text-gray-400">{c.identifier}</code>
                    <span className="text-xs text-gray-700 truncate flex-1">{c.summary}</span>
                    <span className="text-[11px] font-semibold text-gray-600 flex-shrink-0">
                      {c.lines_changed} lines
                    </span>
                  </div>
                </div>
              ))}
            </Section>
          </>
        )}
      </div>
    </AppShell>
  )
}
