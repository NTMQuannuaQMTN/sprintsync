'use client'

import { useParams } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { CheckSquare, Upload } from 'lucide-react'
import Link from 'next/link'
import { reposApi, tasksApi } from '@/lib/api'
import { StatusBadge, PriorityBadge } from '@/components/ui/StatusBadge'
import { SkeletonCard } from '@/components/ui/Skeleton'
import EmptyState from '@/components/ui/EmptyState'
import AppShell from '@/components/layout/AppShell'
import type { Task, TaskStatus } from '@/lib/types'
import { STATUS_LABELS } from '@/lib/types'

const STATUS_OPTIONS: TaskStatus[] = ['todo', 'in_progress', 'done', 'blocked', 'cancelled']

function TaskRow({ repoId, task }: { repoId: string; task: Task }) {
  const queryClient = useQueryClient()
  const updateMutation = useMutation({
    mutationFn: (status: TaskStatus) => tasksApi.update(repoId, task.id, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks', repoId] })
      queryClient.invalidateQueries({ queryKey: ['repo', repoId] })
    },
  })

  return (
    <div className="px-5 py-3 flex items-center gap-3">
      <select
        value={task.status}
        disabled={updateMutation.isPending}
        onChange={(e) => updateMutation.mutate(e.target.value as TaskStatus)}
        className="text-xs border border-gray-200 rounded-md px-1.5 py-1 bg-white focus:outline-none focus:border-gray-400 disabled:opacity-50"
      >
        {STATUS_OPTIONS.map((s) => (
          <option key={s} value={s}>{STATUS_LABELS[s]}</option>
        ))}
      </select>
      <StatusBadge status={task.status} />
      <PriorityBadge priority={task.priority} />
      <span className="flex-1 text-sm text-gray-700 truncate">{task.title}</span>
      {task.ai_tags && task.ai_tags.length > 0 && (
        <div className="hidden sm:flex items-center gap-1">
          {task.ai_tags.slice(0, 3).map((tag) => (
            <span key={tag} className="text-[10px] text-gray-400 bg-gray-50 px-1.5 py-0.5 rounded">
              {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

export default function RepoTasksPage() {
  const { id } = useParams<{ id: string }>()

  const { data: repo } = useQuery({
    queryKey: ['repo', id],
    queryFn: () => reposApi.get(id),
    enabled: !!id,
  })

  const { data: tasks, isLoading } = useQuery({
    queryKey: ['tasks', id],
    queryFn: () => tasksApi.list(id),
    enabled: !!id,
  })

  return (
    <AppShell headerTitle="Tasks" repoId={id} repoName={repo?.name}>
      <div className="p-6 max-w-4xl mx-auto fade-in">
        <div className="bg-white border border-gray-100 rounded-xl">
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-50">
            <span className="text-sm font-semibold text-gray-900">
              All Tasks {tasks ? `(${tasks.length})` : ''}
            </span>
            <Link
              href={`/repositories/${id}/upload`}
              className="text-xs text-[#0F62FE] hover:underline flex items-center gap-1"
            >
              <Upload className="w-3 h-3" /> Upload spec
            </Link>
          </div>

          {isLoading ? (
            <div className="p-4 space-y-2">{[0, 1, 2, 3].map((i) => <SkeletonCard key={i} />)}</div>
          ) : tasks?.length === 0 ? (
            <EmptyState
              icon={CheckSquare}
              title="No tasks yet"
              description="Upload a project specification and AI will extract implementation tasks for review."
              action={
                <Link
                  href={`/repositories/${id}/upload`}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-[#0F62FE] text-white text-sm rounded-lg hover:bg-blue-700 transition-colors font-medium"
                >
                  <Upload className="w-4 h-4" /> Upload Specification
                </Link>
              }
            />
          ) : (
            <div className="divide-y divide-gray-50">
              {tasks?.map((task) => (
                <div key={task.id}>
                  <TaskRow repoId={id} task={task} />
                  {task.subtasks?.map((sub) => (
                    <div key={sub.id} className="pl-10">
                      <TaskRow repoId={id} task={sub} />
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  )
}
