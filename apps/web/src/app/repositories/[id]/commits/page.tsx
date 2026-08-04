'use client'

import { useState } from 'react'
import { useParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { GitCommit, ChevronDown, ChevronRight, FileDiff } from 'lucide-react'
import { reposApi, commitsApi } from '@/lib/api'
import { SkeletonRow } from '@/components/ui/Skeleton'
import EmptyState from '@/components/ui/EmptyState'
import AppShell from '@/components/layout/AppShell'
import { formatRelativeTime } from '@/lib/utils'
import type { CommitDetail } from '@/lib/types'

const STATUS_COLOR: Record<string, string> = {
  added: 'text-emerald-600',
  modified: 'text-amber-600',
  removed: 'text-rose-600',
}

function CommitRow({ commit }: { commit: CommitDetail }) {
  const [expanded, setExpanded] = useState(false)
  const hasFiles = (commit.files_changed?.length ?? 0) > 0

  return (
    <div className="px-5 py-3">
      <button
        onClick={() => hasFiles && setExpanded((v) => !v)}
        className="w-full flex items-start gap-3 text-left"
        disabled={!hasFiles}
      >
        {hasFiles ? (
          expanded ? (
            <ChevronDown className="w-3.5 h-3.5 text-gray-400 mt-0.5 flex-shrink-0" />
          ) : (
            <ChevronRight className="w-3.5 h-3.5 text-gray-400 mt-0.5 flex-shrink-0" />
          )
        ) : (
          <span className="w-3.5 flex-shrink-0" />
        )}
        <div className="flex-1 min-w-0">
          <p className="text-sm text-gray-800 truncate">{commit.message}</p>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <code className="text-[10px] font-mono text-gray-400">{commit.short_sha}</code>
            <span className="text-[10px] text-gray-300">·</span>
            <span className="text-[10px] text-gray-400">{commit.author_name}</span>
            <span className="text-[10px] text-gray-300">·</span>
            <span className="text-[10px] text-gray-400">{formatRelativeTime(commit.committed_at)}</span>
            {(commit.additions > 0 || commit.deletions > 0) && (
              <>
                <span className="text-[10px] text-gray-300">·</span>
                <span className="text-[10px] font-mono text-emerald-600">+{commit.additions}</span>
                <span className="text-[10px] font-mono text-rose-600">-{commit.deletions}</span>
              </>
            )}
            {commit.changed_files > 0 && (
              <span className="text-[10px] text-gray-400 flex items-center gap-0.5">
                <FileDiff className="w-2.5 h-2.5" />
                {commit.changed_files} file{commit.changed_files === 1 ? '' : 's'}
              </span>
            )}
          </div>
        </div>
        <a
          href={commit.html_url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="text-[10px] text-[#0F62FE] hover:underline flex-shrink-0"
        >
          View on GitHub
        </a>
      </button>

      {expanded && hasFiles && (
        <div className="mt-2 ml-6 space-y-1.5">
          {commit.files_changed!.map((f, i) => (
            <div key={i} className="text-xs">
              <div className="flex items-center gap-2">
                <span className={`font-mono ${STATUS_COLOR[f.status] || 'text-gray-500'}`}>
                  {f.status}
                </span>
                <span className="font-mono text-gray-600 truncate">{f.filename}</span>
                {(f.additions > 0 || f.deletions > 0) && (
                  <span className="font-mono text-[10px] text-gray-400 flex-shrink-0">
                    +{f.additions} -{f.deletions}
                  </span>
                )}
              </div>
              {f.patch && (
                <pre className="mt-1 mb-2 p-2 bg-gray-50 border border-gray-100 rounded-md text-[10px] font-mono text-gray-600 overflow-x-auto max-h-48 overflow-y-auto whitespace-pre">
                  {f.patch}
                </pre>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function RepoCommitsPage() {
  const { id } = useParams<{ id: string }>()

  const { data: repo } = useQuery({
    queryKey: ['repo', id],
    queryFn: () => reposApi.get(id),
    enabled: !!id,
  })

  const { data: commits, isLoading } = useQuery({
    queryKey: ['commits', id],
    queryFn: () => commitsApi.list(id, 50),
    enabled: !!id,
  })

  return (
    <AppShell headerTitle="Commits" repoId={id} repoName={repo?.name}>
      <div className="p-6 max-w-4xl mx-auto fade-in">
        <div className="bg-white border border-gray-100 rounded-xl">
          <div className="px-5 py-4 border-b border-gray-50">
            <span className="text-sm font-semibold text-gray-900">
              Recent Commits {commits ? `(${commits.length})` : ''}
            </span>
          </div>

          {isLoading ? (
            <div className="p-4 space-y-2">{[0, 1, 2, 3].map((i) => <SkeletonRow key={i} />)}</div>
          ) : commits?.length === 0 ? (
            <EmptyState
              icon={GitCommit}
              title="No commits yet"
              description="Once this repo's webhook is active, pushed commits will show up here with the files they touched."
            />
          ) : (
            <div className="divide-y divide-gray-50">
              {commits?.map((c) => <CommitRow key={c.id} commit={c} />)}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  )
}
