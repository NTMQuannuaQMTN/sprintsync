'use client'

import { useParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import {
  Activity as ActivityIcon,
  GitCommit,
  Upload,
  ListChecks,
  Sparkles,
  Check,
  X,
  Pencil,
  Webhook,
  GitBranch,
} from 'lucide-react'
import { reposApi, activityApi } from '@/lib/api'
import { SkeletonRow } from '@/components/ui/Skeleton'
import EmptyState from '@/components/ui/EmptyState'
import AppShell from '@/components/layout/AppShell'
import { formatRelativeTime } from '@/lib/utils'
import type { ActivityItem } from '@/lib/types'

const EVENT_META: Record<string, { icon: typeof ActivityIcon; color: string; bg: string }> = {
  repo_connected: { icon: GitBranch, color: 'text-blue-600', bg: 'bg-blue-50' },
  spec_uploaded: { icon: Upload, color: 'text-indigo-600', bg: 'bg-indigo-50' },
  tasks_generated: { icon: ListChecks, color: 'text-purple-600', bg: 'bg-purple-50' },
  commit_received: { icon: GitCommit, color: 'text-gray-600', bg: 'bg-gray-100' },
  suggestion_created: { icon: Sparkles, color: 'text-amber-600', bg: 'bg-amber-50' },
  suggestion_approved: { icon: Check, color: 'text-emerald-600', bg: 'bg-emerald-50' },
  suggestion_rejected: { icon: X, color: 'text-rose-600', bg: 'bg-rose-50' },
  task_updated: { icon: Pencil, color: 'text-blue-600', bg: 'bg-blue-50' },
  webhook_installed: { icon: Webhook, color: 'text-gray-600', bg: 'bg-gray-100' },
}

function EventRow({ item }: { item: ActivityItem }) {
  const meta = EVENT_META[item.event_type] ?? { icon: ActivityIcon, color: 'text-gray-500', bg: 'bg-gray-100' }
  const Icon = meta.icon
  return (
    <div className="flex items-start gap-3 px-5 py-4">
      <div className={`w-7 h-7 rounded-full ${meta.bg} ${meta.color} flex items-center justify-center flex-shrink-0 mt-0.5`}>
        <Icon className="w-3.5 h-3.5" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-800">{item.title}</p>
        {item.description && <p className="text-xs text-gray-500 mt-0.5">{item.description}</p>}
        <p className="text-[10px] text-gray-400 mt-1">{formatRelativeTime(item.created_at)}</p>
      </div>
    </div>
  )
}

export default function RepoActivityPage() {
  const { id } = useParams<{ id: string }>()

  const { data: repo } = useQuery({
    queryKey: ['repo', id],
    queryFn: () => reposApi.get(id),
    enabled: !!id,
  })

  const { data: activity, isLoading } = useQuery({
    queryKey: ['activity', id],
    queryFn: () => activityApi.list(id, 100),
    enabled: !!id,
    refetchInterval: 30_000,
  })

  return (
    <AppShell headerTitle="Activity" repoId={id} repoName={repo?.name}>
      <div className="p-6 max-w-3xl mx-auto fade-in">
        <div className="bg-white border border-gray-100 rounded-xl">
          <div className="px-5 py-4 border-b border-gray-50">
            <span className="text-sm font-semibold text-gray-900">Activity Timeline</span>
          </div>

          {isLoading ? (
            <div className="p-4 space-y-2">{[0, 1, 2, 3].map((i) => <SkeletonRow key={i} />)}</div>
          ) : activity?.length === 0 ? (
            <EmptyState
              icon={ActivityIcon}
              title="No activity yet"
              description="Connect this repo's webhook and push a commit to see activity here."
            />
          ) : (
            <div className="divide-y divide-gray-50">
              {activity?.map((item) => <EventRow key={item.id} item={item} />)}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  )
}
