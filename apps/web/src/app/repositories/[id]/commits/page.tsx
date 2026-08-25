'use client'

import { useState } from 'react'
import { useParams } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  GitCommit, GitPullRequest, ChevronDown, ChevronRight, FileDiff, Sparkles, Loader2, MessageSquareText,
} from 'lucide-react'
import { reposApi, commitsApi, pullRequestsApi } from '@/lib/api'
import { SkeletonRow } from '@/components/ui/Skeleton'
import EmptyState from '@/components/ui/EmptyState'
import AppShell from '@/components/layout/AppShell'
import { cn, formatRelativeTime } from '@/lib/utils'
import type { CommitDetail, PullRequest } from '@/lib/types'

function SummarizeButton({ onSummarize }: { onSummarize: () => Promise<{ summary: string; source: string }> }) {
  const [result, setResult] = useState<{ summary: string; source: string } | null>(null)
  const mutation = useMutation({ mutationFn: onSummarize, onSuccess: setResult })

  if (result) {
    return (
      <p className="text-[11px] text-gray-600 mt-1.5 flex items-start gap-1">
        <MessageSquareText className="w-3 h-3 text-violet-500 flex-shrink-0 mt-0.5" />
        <span>
          {result.summary}{' '}
          <span className="text-gray-400">({result.source === 'llm' ? 'AI' : 'heuristic'})</span>
        </span>
      </p>
    )
  }

  return (
    <button
      onClick={(e) => {
        e.stopPropagation()
        mutation.mutate()
      }}
      disabled={mutation.isPending}
      className="text-[10px] text-violet-600 hover:underline flex items-center gap-1 mt-1 disabled:opacity-50"
    >
      {mutation.isPending ? <Loader2 className="w-2.5 h-2.5 animate-spin" /> : <MessageSquareText className="w-2.5 h-2.5" />}
      Summarize
    </button>
  )
}

const STATUS_COLOR: Record<string, string> = {
  added: 'text-emerald-600',
  modified: 'text-amber-600',
  removed: 'text-rose-600',
}

function CommitRow({ repoId, commit }: { repoId: string; commit: CommitDetail }) {
  const [expanded, setExpanded] = useState(false)
  const hasFiles = (commit.files_changed?.length ?? 0) > 0

  return (
    <div className="px-5 py-3">
      {/* Not a <button> (unlike the rest of this row's original design) --
          it now contains real interactive children (SummarizeButton), and
          nesting a <button> inside a <button> is invalid HTML. */}
      <div
        role="button"
        tabIndex={hasFiles ? 0 : -1}
        onClick={() => hasFiles && setExpanded((v) => !v)}
        onKeyDown={(e) => {
          if (hasFiles && (e.key === 'Enter' || e.key === ' ')) setExpanded((v) => !v)
        }}
        className="w-full flex items-start gap-3 text-left cursor-default"
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
          <SummarizeButton onSummarize={() => commitsApi.summary(repoId, commit.id)} />
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
      </div>

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

const PR_STATE_STYLE: Record<string, string> = {
  open: 'bg-emerald-50 text-emerald-700',
  merged: 'bg-violet-50 text-violet-700',
  closed: 'bg-gray-100 text-gray-500',
}

function PRRow({ repoId, pr }: { repoId: string; pr: PullRequest }) {
  return (
    <div className="px-5 py-3">
      <div className="flex items-start gap-3">
        <span className={cn('text-[10px] font-medium px-1.5 py-0.5 rounded flex-shrink-0 mt-0.5', PR_STATE_STYLE[pr.state])}>
          {pr.state}
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-gray-800 truncate">
            #{pr.number} {pr.title}
          </p>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <code className="text-[10px] font-mono text-gray-400">{pr.branch}</code>
            <span className="text-[10px] text-gray-300">·</span>
            <span className="text-[10px] text-gray-400">{pr.author}</span>
            <span className="text-[10px] text-gray-300">·</span>
            <span className="text-[10px] text-gray-400">{formatRelativeTime(pr.opened_at)}</span>
            {(pr.additions > 0 || pr.deletions > 0) && (
              <>
                <span className="text-[10px] text-gray-300">·</span>
                <span className="text-[10px] font-mono text-emerald-600">+{pr.additions}</span>
                <span className="text-[10px] font-mono text-rose-600">-{pr.deletions}</span>
              </>
            )}
          </div>
          <SummarizeButton onSummarize={() => pullRequestsApi.summary(repoId, pr.id)} />
        </div>
        <a
          href={pr.html_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[10px] text-[#0F62FE] hover:underline flex-shrink-0"
        >
          View on GitHub
        </a>
      </div>
    </div>
  )
}

export default function RepoCommitsPage() {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()
  const [tab, setTab] = useState<'commits' | 'pull_requests'>('commits')

  const { data: repo } = useQuery({
    queryKey: ['repo', id],
    queryFn: () => reposApi.get(id),
    enabled: !!id,
  })

  const { data: commits, isLoading } = useQuery({
    queryKey: ['commits', id],
    queryFn: () => commitsApi.list(id, 50),
    enabled: !!id && tab === 'commits',
  })

  const { data: pullRequests, isLoading: loadingPRs } = useQuery({
    queryKey: ['pull_requests', id],
    queryFn: () => pullRequestsApi.list(id, 50),
    enabled: !!id && tab === 'pull_requests',
  })

  const analyzeMutation = useMutation({
    mutationFn: () => commitsApi.analyze(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['commits', id] })
      queryClient.invalidateQueries({ queryKey: ['suggestions', id] })
    },
  })

  const headerActions = (
    <button
      onClick={() => analyzeMutation.mutate()}
      disabled={analyzeMutation.isPending}
      className="flex items-center gap-1.5 px-3 py-1.5 bg-[#0F62FE] text-white text-xs rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50"
    >
      {analyzeMutation.isPending ? (
        <Loader2 className="w-3.5 h-3.5 animate-spin" />
      ) : (
        <Sparkles className="w-3.5 h-3.5" />
      )}
      Update to tasks
    </button>
  )

  return (
    <AppShell headerTitle="Commits" repoId={id} repoName={repo?.name} headerActions={headerActions}>
      <div className="p-6 max-w-4xl mx-auto fade-in">
        <div className="flex items-center gap-1 mb-4 bg-gray-50 rounded-lg p-0.5 w-fit">
          {(['commits', 'pull_requests'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors',
                tab === t ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700',
              )}
            >
              {t === 'commits' ? <GitCommit className="w-3.5 h-3.5" /> : <GitPullRequest className="w-3.5 h-3.5" />}
              {t === 'commits' ? 'Commits' : 'Pull Requests'}
            </button>
          ))}
        </div>

        {analyzeMutation.isSuccess && (
          <div className="mb-4 px-4 py-3 bg-blue-50 border border-blue-100 rounded-lg text-sm text-blue-800">
            {analyzeMutation.data.commits_processed === 0
              ? 'Nothing new to analyze — every commit has already been reviewed.'
              : `Reviewed ${analyzeMutation.data.commits_processed} commit${analyzeMutation.data.commits_processed === 1 ? '' : 's'} and created ${analyzeMutation.data.suggestions_created} suggestion${analyzeMutation.data.suggestions_created === 1 ? '' : 's'} for review.`}
            {analyzeMutation.data.suggestions_created > 0 && (
              <>
                {' '}
                <a href={`/repositories/${id}/suggestions`} className="underline font-medium">
                  Review suggestions
                </a>
              </>
            )}
          </div>
        )}
        {analyzeMutation.isError && (
          <div className="mb-4 px-4 py-3 bg-rose-50 border border-rose-100 rounded-lg text-sm text-rose-700">
            {(analyzeMutation.error as Error).message || 'Could not analyze commits'}
          </div>
        )}
        {tab === 'commits' ? (
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
                {commits?.map((c) => <CommitRow key={c.id} repoId={id} commit={c} />)}
              </div>
            )}
          </div>
        ) : (
          <div className="bg-white border border-gray-100 rounded-xl">
            <div className="px-5 py-4 border-b border-gray-50">
              <span className="text-sm font-semibold text-gray-900">
                Pull Requests {pullRequests ? `(${pullRequests.length})` : ''}
              </span>
            </div>

            {loadingPRs ? (
              <div className="p-4 space-y-2">{[0, 1, 2, 3].map((i) => <SkeletonRow key={i} />)}</div>
            ) : pullRequests?.length === 0 ? (
              <EmptyState
                icon={GitPullRequest}
                title="No pull requests yet"
                description="Once this repo's webhook is active, opened/merged/closed PRs will show up here."
              />
            ) : (
              <div className="divide-y divide-gray-50">
                {pullRequests?.map((pr) => <PRRow key={pr.id} repoId={id} pr={pr} />)}
              </div>
            )}
          </div>
        )}
      </div>
    </AppShell>
  )
}
