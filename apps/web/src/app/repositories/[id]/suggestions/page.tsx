'use client'

import { useState } from 'react'
import { useParams } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Sparkles, Check, X, GitCommit } from 'lucide-react'
import { reposApi, suggestionsApi } from '@/lib/api'
import { ConfidenceBar } from '@/components/ui/ConfidenceBar'
import { SkeletonCard } from '@/components/ui/Skeleton'
import EmptyState from '@/components/ui/EmptyState'
import AppShell from '@/components/layout/AppShell'
import { cn } from '@/lib/utils'
import { formatRelativeTime } from '@/lib/utils'
import type { Suggestion, SuggestionStatus } from '@/lib/types'

const TABS: { id: SuggestionStatus; label: string }[] = [
  { id: 'pending', label: 'Pending' },
  { id: 'approved', label: 'Approved' },
  { id: 'rejected', label: 'Rejected' },
]

function SuggestionCard({ repoId, suggestion }: { repoId: string; suggestion: Suggestion }) {
  const queryClient = useQueryClient()
  const [note, setNote] = useState('')
  const [showNote, setShowNote] = useState<'approve' | 'reject' | null>(null)

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['suggestions', repoId] })
    queryClient.invalidateQueries({ queryKey: ['tasks', repoId] })
    queryClient.invalidateQueries({ queryKey: ['repo', repoId] })
  }

  const approveMutation = useMutation({
    mutationFn: () => suggestionsApi.approve(repoId, suggestion.id, note || undefined),
    onSuccess: invalidate,
  })
  const rejectMutation = useMutation({
    mutationFn: () => suggestionsApi.reject(repoId, suggestion.id, note || undefined),
    onSuccess: invalidate,
  })

  const pending = suggestion.status === 'pending'
  const busy = approveMutation.isPending || rejectMutation.isPending

  return (
    <div className="px-5 py-4 border-b border-gray-50 last:border-0">
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900">
            {suggestion.task_title || 'Untitled task'}
          </p>
          {suggestion.proposed_status && (
            <p className="text-xs text-gray-500 mt-0.5">
              Proposed status: <span className="font-medium text-gray-700">{suggestion.proposed_status}</span>
            </p>
          )}
        </div>
        <ConfidenceBar score={suggestion.confidence_score} className="w-28 flex-shrink-0" />
      </div>

      <p className="text-xs text-gray-600 mb-2">{suggestion.explanation}</p>

      {suggestion.commit_sha && (
        <div className="flex items-center gap-1.5 text-[11px] text-gray-400 mb-2">
          <GitCommit className="w-3 h-3" />
          <code className="font-mono">{suggestion.commit_sha}</code>
          <span className="truncate">{suggestion.commit_message}</span>
        </div>
      )}

      {suggestion.evidence && (
        <div className="bg-gray-50 border border-gray-100 rounded-lg p-3 mb-3 space-y-1">
          {suggestion.evidence.matching_keywords && suggestion.evidence.matching_keywords.length > 0 && (
            <p className="text-[11px] text-gray-500">
              <span className="font-medium text-gray-600">Matching keywords:</span>{' '}
              {suggestion.evidence.matching_keywords.join(', ')}
            </p>
          )}
          {suggestion.evidence.matching_files && suggestion.evidence.matching_files.length > 0 && (
            <p className="text-[11px] text-gray-500 font-mono">
              <span className="font-sans font-medium text-gray-600 mr-1">Files:</span>
              {suggestion.evidence.matching_files.join(', ')}
            </p>
          )}
        </div>
      )}

      <div className="flex items-center justify-between">
        <span className="text-[10px] text-gray-400">{formatRelativeTime(suggestion.created_at)}</span>

        {pending ? (
          <div className="flex items-center gap-2">
            {showNote && (
              <input
                autoFocus
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Optional note…"
                className="text-xs border border-gray-200 rounded-md px-2 py-1 w-40 focus:outline-none focus:border-gray-400"
              />
            )}
            <button
              onClick={() => (showNote === 'reject' ? rejectMutation.mutate() : setShowNote('reject'))}
              disabled={busy}
              className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-rose-600 hover:bg-rose-50 rounded-md transition-colors disabled:opacity-50"
            >
              <X className="w-3 h-3" /> Reject
            </button>
            <button
              onClick={() => (showNote === 'approve' ? approveMutation.mutate() : setShowNote('approve'))}
              disabled={busy}
              className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium bg-[#16A34A] text-white hover:bg-green-700 rounded-md transition-colors disabled:opacity-50"
            >
              <Check className="w-3 h-3" /> Approve
            </button>
          </div>
        ) : (
          <span
            className={cn(
              'text-[11px] font-medium px-2 py-0.5 rounded-full',
              suggestion.status === 'approved' ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-gray-500',
            )}
          >
            {suggestion.status === 'approved' ? 'Approved' : 'Rejected'}
            {suggestion.reviewer_note ? ` — ${suggestion.reviewer_note}` : ''}
          </span>
        )}
      </div>
    </div>
  )
}

export default function RepoSuggestionsPage() {
  const { id } = useParams<{ id: string }>()
  const [tab, setTab] = useState<SuggestionStatus>('pending')

  const { data: repo } = useQuery({
    queryKey: ['repo', id],
    queryFn: () => reposApi.get(id),
    enabled: !!id,
  })

  const { data: suggestions, isLoading } = useQuery({
    queryKey: ['suggestions', id, tab],
    queryFn: () => suggestionsApi.list(id, tab),
    enabled: !!id,
  })

  return (
    <AppShell headerTitle="AI Suggestions" repoId={id} repoName={repo?.name}>
      <div className="p-6 max-w-3xl mx-auto fade-in">
        <div className="bg-white border border-gray-100 rounded-xl">
          <div className="flex items-center gap-1 px-3 pt-3 border-b border-gray-50">
            {TABS.map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={cn(
                  'px-3 py-2 text-xs font-medium rounded-t-lg transition-colors',
                  tab === t.id
                    ? 'text-[#0F62FE] border-b-2 border-[#0F62FE]'
                    : 'text-gray-500 hover:text-gray-700',
                )}
              >
                {t.label}
              </button>
            ))}
          </div>

          {isLoading ? (
            <div className="p-4 space-y-2">{[0, 1].map((i) => <SkeletonCard key={i} />)}</div>
          ) : suggestions?.length === 0 ? (
            <EmptyState
              icon={Sparkles}
              title={`No ${tab} suggestions`}
              description={
                tab === 'pending'
                  ? 'AI-generated suggestions appear here after commits are pushed to this repository.'
                  : undefined
              }
            />
          ) : (
            <div>
              {suggestions?.map((s) => (
                <SuggestionCard key={s.id} repoId={id} suggestion={s} />
              ))}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  )
}
