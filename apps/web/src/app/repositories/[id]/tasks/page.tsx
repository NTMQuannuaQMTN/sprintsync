'use client'

import { useState } from 'react'
import { useParams } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { CheckSquare, Upload, Plus, Loader2, X, Trash2, Check } from 'lucide-react'
import Link from 'next/link'
import { reposApi, tasksApi } from '@/lib/api'
import { StatusBadge, PriorityBadge } from '@/components/ui/StatusBadge'
import { SkeletonCard } from '@/components/ui/Skeleton'
import EmptyState from '@/components/ui/EmptyState'
import AppShell from '@/components/layout/AppShell'
import type { Task, TaskStatus, TaskPriority } from '@/lib/types'
import { STATUS_LABELS, PRIORITY_LABELS } from '@/lib/types'

const STATUS_OPTIONS: TaskStatus[] = ['todo', 'in_progress', 'done', 'blocked', 'cancelled']
const PRIORITY_OPTIONS: TaskPriority[] = ['low', 'medium', 'high', 'critical']

function TaskRow({ repoId, task }: { repoId: string; task: Task }) {
  const queryClient = useQueryClient()
  const [confirmingDelete, setConfirmingDelete] = useState(false)

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['tasks', repoId] })
    queryClient.invalidateQueries({ queryKey: ['repo', repoId] })
  }

  const updateMutation = useMutation({
    mutationFn: (status: TaskStatus) => tasksApi.update(repoId, task.id, { status }),
    onSuccess: invalidate,
  })

  const deleteMutation = useMutation({
    mutationFn: () => tasksApi.delete(repoId, task.id),
    onSuccess: invalidate,
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
      {confirmingDelete ? (
        <div className="flex items-center gap-1 flex-shrink-0">
          <span className="text-[10px] text-gray-400 mr-0.5">Delete?</span>
          <button
            onClick={() => deleteMutation.mutate()}
            disabled={deleteMutation.isPending}
            className="p-1 text-rose-600 hover:bg-rose-50 rounded-md transition-colors disabled:opacity-50"
            title="Confirm delete"
          >
            {deleteMutation.isPending ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Check className="w-3.5 h-3.5" />
            )}
          </button>
          <button
            onClick={() => setConfirmingDelete(false)}
            disabled={deleteMutation.isPending}
            className="p-1 text-gray-400 hover:bg-gray-100 rounded-md transition-colors"
            title="Cancel"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      ) : (
        <button
          onClick={() => setConfirmingDelete(true)}
          className="p-1 text-gray-300 hover:text-rose-600 hover:bg-rose-50 rounded-md transition-colors flex-shrink-0"
          title="Delete task"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  )
}

function AddTaskForm({ repoId, onClose }: { repoId: string; onClose: () => void }) {
  const queryClient = useQueryClient()
  const [title, setTitle] = useState('')
  const [priority, setPriority] = useState<TaskPriority>('medium')

  const createMutation = useMutation({
    mutationFn: () => tasksApi.create(repoId, { title: title.trim(), priority }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks', repoId] })
      queryClient.invalidateQueries({ queryKey: ['repo', repoId] })
      onClose()
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim() || createMutation.isPending) return
    createMutation.mutate()
  }

  return (
    <form onSubmit={handleSubmit} className="px-5 py-4 border-b border-gray-50 bg-gray-50/50">
      <div className="flex items-center gap-2">
        <input
          autoFocus
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Task title…"
          className="flex-1 text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-[#0F62FE]/20 focus:border-[#0F62FE]"
        />
        <select
          value={priority}
          onChange={(e) => setPriority(e.target.value as TaskPriority)}
          className="text-sm border border-gray-200 rounded-lg px-2 py-2 bg-white focus:outline-none"
        >
          {PRIORITY_OPTIONS.map((p) => (
            <option key={p} value={p}>{PRIORITY_LABELS[p]}</option>
          ))}
        </select>
        <button
          type="submit"
          disabled={!title.trim() || createMutation.isPending}
          className="flex items-center gap-1.5 px-3 py-2 bg-[#0F62FE] text-white text-sm rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50"
        >
          {createMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Add'}
        </button>
        <button
          type="button"
          onClick={onClose}
          className="p-2 text-gray-400 hover:text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
      {createMutation.isError && (
        <p className="text-xs text-rose-600 mt-2">
          {(createMutation.error as Error).message || 'Could not create task'}
        </p>
      )}
    </form>
  )
}

export default function RepoTasksPage() {
  const { id } = useParams<{ id: string }>()
  const [showAddForm, setShowAddForm] = useState(false)

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
            <div className="flex items-center gap-3">
              <Link
                href={`/repositories/${id}/upload`}
                className="text-xs text-[#0F62FE] hover:underline flex items-center gap-1"
              >
                <Upload className="w-3 h-3" /> Upload spec
              </Link>
              {!showAddForm && (
                <button
                  onClick={() => setShowAddForm(true)}
                  className="flex items-center gap-1 px-2.5 py-1 bg-gray-900 text-white text-xs rounded-lg hover:bg-gray-800 transition-colors font-medium"
                >
                  <Plus className="w-3 h-3" /> Add Task
                </button>
              )}
            </div>
          </div>

          {showAddForm && <AddTaskForm repoId={id} onClose={() => setShowAddForm(false)} />}

          {isLoading ? (
            <div className="p-4 space-y-2">{[0, 1, 2, 3].map((i) => <SkeletonCard key={i} />)}</div>
          ) : tasks?.length === 0 ? (
            <EmptyState
              icon={CheckSquare}
              title="No tasks yet"
              description="Add one manually, or upload a project specification and let AI extract a full checklist for review."
              action={
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setShowAddForm(true)}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-gray-900 text-white text-sm rounded-lg hover:bg-gray-800 transition-colors font-medium"
                  >
                    <Plus className="w-4 h-4" /> Add Task
                  </button>
                  <Link
                    href={`/repositories/${id}/upload`}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-[#0F62FE] text-white text-sm rounded-lg hover:bg-blue-700 transition-colors font-medium"
                  >
                    <Upload className="w-4 h-4" /> Upload Specification
                  </Link>
                </div>
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
