'use client'

import { useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Upload, FileText, Loader2, CheckSquare, Square, ArrowRight, Link as LinkIcon } from 'lucide-react'
import { reposApi, specsApi, tasksApi } from '@/lib/api'
import { PriorityBadge } from '@/components/ui/StatusBadge'
import AppShell from '@/components/layout/AppShell'
import { formatBytes } from '@/lib/utils'
import type { ProjectSpec, DraftTask, TaskPriority } from '@/lib/types'
import { PRIORITY_LABELS } from '@/lib/types'

interface ReviewItem extends DraftTask {
  selected: boolean
}

export default function UploadSpecPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const [file, setFile] = useState<File | null>(null)
  const [docLink, setDocLink] = useState('')
  const [spec, setSpec] = useState<ProjectSpec | null>(null)
  const [items, setItems] = useState<ReviewItem[]>([])

  const { data: repo } = useQuery({
    queryKey: ['repo', id],
    queryFn: () => reposApi.get(id),
    enabled: !!id,
  })

  const onSpecReady = (result: ProjectSpec) => {
    setSpec(result)
    setItems(result.draft_tasks.map((t) => ({ ...t, selected: true })))
  }

  const uploadMutation = useMutation({
    mutationFn: (f: File) => specsApi.upload(id, f),
    onSuccess: onSpecReady,
  })

  const linkMutation = useMutation({
    mutationFn: () => specsApi.uploadFromLink(id, docLink),
    onSuccess: onSpecReady,
  })

  const intakeBusy = uploadMutation.isPending || linkMutation.isPending

  const saveMutation = useMutation({
    mutationFn: () => {
      const selected = items.filter((i) => i.selected)
      return tasksApi.bulkCreate(
        id,
        selected.map(({ selected: _s, ...t }) => t),
        spec?.id,
      )
    },
    onSuccess: () => router.push(`/repositories/${id}/tasks`),
  })

  const selectedCount = items.filter((i) => i.selected).length

  const toggle = (index: number) => {
    setItems((prev) => prev.map((it, i) => (i === index ? { ...it, selected: !it.selected } : it)))
  }
  const updateTitle = (index: number, title: string) => {
    setItems((prev) => prev.map((it, i) => (i === index ? { ...it, title } : it)))
  }
  const updatePriority = (index: number, priority: TaskPriority) => {
    setItems((prev) => prev.map((it, i) => (i === index ? { ...it, priority } : it)))
  }

  return (
    <AppShell headerTitle="Upload Specification" repoId={id} repoName={repo?.name}>
      <div className="p-6 max-w-3xl mx-auto fade-in space-y-6">
        {!spec ? (
          <>
            <div className="bg-white border border-gray-100 rounded-xl p-8">
              <div className="w-12 h-12 bg-blue-50 rounded-2xl flex items-center justify-center mb-4">
                <Upload className="w-6 h-6 text-blue-700" />
              </div>
              <h2 className="text-base font-semibold text-gray-900 mb-1">Upload a project specification</h2>
              <p className="text-sm text-gray-500 mb-5">
                PDF or DOCX, up to 10MB. AI will extract a draft implementation checklist — nothing is
                saved until you review and confirm it below.
              </p>

              <label className="flex items-center justify-between gap-3 border border-dashed border-gray-300 rounded-lg px-4 py-3 cursor-pointer hover:border-gray-400 transition-colors">
                <div className="flex items-center gap-2 min-w-0">
                  <FileText className="w-4 h-4 text-gray-400 flex-shrink-0" />
                  <span className="text-sm text-gray-600 truncate">
                    {file ? file.name : 'Choose a PDF or DOCX file…'}
                  </span>
                </div>
                {file && <span className="text-xs text-gray-400 flex-shrink-0">{formatBytes(file.size)}</span>}
                <input
                  type="file"
                  accept=".pdf,.docx,.doc,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                  className="hidden"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                />
              </label>

              {uploadMutation.isError && (
                <p className="text-xs text-rose-600 mt-3">
                  {(uploadMutation.error as Error).message || 'Upload failed'}
                </p>
              )}

              <button
                onClick={() => file && uploadMutation.mutate(file)}
                disabled={!file || intakeBusy}
                className="mt-5 flex items-center gap-2 px-4 py-2 bg-[#0F62FE] text-white text-sm rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50"
              >
                {uploadMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" /> Analyzing…
                  </>
                ) : (
                  'Upload & Analyze'
                )}
              </button>
            </div>

            <div className="bg-white border border-gray-100 rounded-xl p-8">
              <div className="w-12 h-12 bg-blue-50 rounded-2xl flex items-center justify-center mb-4">
                <LinkIcon className="w-6 h-6 text-blue-700" />
              </div>
              <h2 className="text-base font-semibold text-gray-900 mb-1">Or paste a Google Docs link</h2>
              <p className="text-sm text-gray-500 mb-5">
                The doc must be shared as "Anyone with the link" (Viewer) — this app can't read
                restricted documents.
              </p>

              <div className="flex items-center gap-3 border border-dashed border-gray-300 rounded-lg px-4 py-3 focus-within:border-gray-400 transition-colors">
                <LinkIcon className="w-4 h-4 text-gray-400 flex-shrink-0" />
                <input
                  type="url"
                  value={docLink}
                  onChange={(e) => setDocLink(e.target.value)}
                  placeholder="https://docs.google.com/document/d/…"
                  className="flex-1 text-sm text-gray-700 bg-transparent focus:outline-none min-w-0"
                />
              </div>

              {linkMutation.isError && (
                <p className="text-xs text-rose-600 mt-3">
                  {(linkMutation.error as Error).message || 'Could not process this Google Doc'}
                </p>
              )}

              <button
                onClick={() => docLink.trim() && linkMutation.mutate()}
                disabled={!docLink.trim() || intakeBusy}
                className="mt-5 flex items-center gap-2 px-4 py-2 bg-[#0F62FE] text-white text-sm rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50"
              >
                {linkMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" /> Analyzing…
                  </>
                ) : (
                  'Analyze'
                )}
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="bg-white border border-gray-100 rounded-xl p-5">
              <p className="text-sm text-gray-700">{spec.ai_summary}</p>
            </div>

            <div className="bg-white border border-gray-100 rounded-xl">
              <div className="flex items-center justify-between px-5 py-4 border-b border-gray-50">
                <span className="text-sm font-semibold text-gray-900">
                  Review draft tasks ({selectedCount}/{items.length} selected)
                </span>
              </div>
              <div className="divide-y divide-gray-50 max-h-[28rem] overflow-y-auto">
                {items.map((item, i) => (
                  <div key={i} className="flex items-start gap-3 px-5 py-3">
                    <button onClick={() => toggle(i)} className="mt-0.5 text-gray-400 hover:text-[#0F62FE] flex-shrink-0">
                      {item.selected ? <CheckSquare className="w-4 h-4 text-[#0F62FE]" /> : <Square className="w-4 h-4" />}
                    </button>
                    <input
                      value={item.title}
                      onChange={(e) => updateTitle(i, e.target.value)}
                      className="flex-1 text-sm text-gray-800 border-none focus:outline-none focus:ring-1 focus:ring-[#0F62FE]/30 rounded px-1 -mx-1 disabled:opacity-50 bg-transparent"
                      disabled={!item.selected}
                    />
                    <select
                      value={item.priority}
                      onChange={(e) => updatePriority(i, e.target.value as TaskPriority)}
                      disabled={!item.selected}
                      className="text-xs border border-gray-200 rounded-md px-1.5 py-1 bg-white focus:outline-none disabled:opacity-50 flex-shrink-0"
                    >
                      {(Object.keys(PRIORITY_LABELS) as TaskPriority[]).map((p) => (
                        <option key={p} value={p}>{PRIORITY_LABELS[p]}</option>
                      ))}
                    </select>
                    <PriorityBadge priority={item.priority} className="hidden sm:inline-flex flex-shrink-0" />
                  </div>
                ))}
              </div>
              <div className="px-5 py-4 border-t border-gray-50 flex items-center justify-between gap-3">
                {saveMutation.isError && (
                  <p className="text-xs text-rose-600 flex-1 min-w-0 truncate">
                    {(saveMutation.error as Error).message || 'Could not save tasks'}
                  </p>
                )}
                <button
                  onClick={() => saveMutation.mutate()}
                  disabled={selectedCount === 0 || saveMutation.isPending}
                  className="flex items-center gap-2 px-4 py-2 bg-[#16A34A] text-white text-sm rounded-lg hover:bg-green-700 transition-colors font-medium disabled:opacity-50 flex-shrink-0 ml-auto"
                >
                  {saveMutation.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      Save {selectedCount} task{selectedCount === 1 ? '' : 's'}
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </AppShell>
  )
}
