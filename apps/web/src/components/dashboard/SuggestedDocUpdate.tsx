'use client'

import { useState } from 'react'
import {
  Sparkles, CheckCircle2, XCircle, Pencil, FileCode,
  ChevronDown, ChevronUp, Lightbulb, ArrowRight, Send
} from 'lucide-react'
import { NotionIcon } from '@/components/ui/NotionIcon'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { approveSuggestion, rejectSuggestion } from '@/lib/utils'
import type { Suggestion } from '@/lib/types'

interface SuggestedDocUpdateProps {
  suggestion: Suggestion
}

export function SuggestedDocUpdate({ suggestion: initial }: SuggestedDocUpdateProps) {
  const [suggestion, setSuggestion] = useState(initial)
  const [isEditing, setIsEditing] = useState(false)
  const [editValue, setEditValue] = useState(initial.suggestedProgress)
  const [showReasoning, setShowReasoning] = useState(false)
  const [loading, setLoading] = useState<'approve' | 'reject' | null>(null)

  async function handleApprove() {
    setLoading('approve')
    try {
      const finalProgress = isEditing ? editValue : suggestion.suggestedProgress
      await approveSuggestion(suggestion.id, isEditing ? editValue : undefined)
      setSuggestion(s => ({ ...s, status: 'approved', suggestedProgress: finalProgress }))
      setIsEditing(false)
    } catch (err) {
      console.error('Failed to approve suggestion:', err)
    } finally {
      setLoading(null)
    }
  }

  async function handleReject() {
    setLoading('reject')
    try {
      await rejectSuggestion(suggestion.id)
      setSuggestion(s => ({ ...s, status: 'rejected' }))
    } catch (err) {
      console.error('Failed to reject suggestion:', err)
    } finally {
      setLoading(null)
    }
  }

  function handleEdit() {
    setEditValue(suggestion.suggestedProgress)
    setIsEditing(true)
  }

  const isDone = suggestion.status === 'approved' || suggestion.status === 'rejected'

  return (
    <div className={`bg-white border rounded-xl shadow-sm overflow-hidden transition-all ${
      suggestion.status === 'approved' ? 'border-green-200' :
      suggestion.status === 'rejected' ? 'border-gray-200 opacity-60' :
      'border-gray-200'
    }`}>
      {/* Header */}
      <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-violet-500" strokeWidth={1.75} />
          <h2 className="text-[14px] font-semibold text-gray-900">Suggested Documentation Update</h2>
          {isDone && (
            <StatusBadge status={suggestion.status} />
          )}
        </div>
        <div className="flex items-center gap-2">
          <NotionIcon className="w-4 h-4" />
          <span className="text-[12px] text-gray-500">Notion</span>
        </div>
      </div>

      <div className="p-5 space-y-4">
        {/* Related Task */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[12px] font-semibold text-gray-700 bg-gray-100 px-2 py-0.5 rounded">
              {suggestion.relatedTask.id}
            </span>
            <span className="text-[13px] font-semibold text-gray-900">{suggestion.relatedTask.title}</span>
          </div>
          <div className="flex items-center gap-1.5 ml-auto">
            <StatusBadge status={suggestion.relatedTask.type} />
            <StatusBadge status={suggestion.relatedTask.priority} />
          </div>
        </div>

        {/* Progress comparison */}
        <div className="grid grid-cols-2 gap-3">
          {/* Existing */}
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-100">
            <div className="flex items-center gap-1.5 mb-2">
              <div className="w-2 h-2 bg-gray-400 rounded-full" />
              <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Existing Progress</span>
            </div>
            <p className={`text-[13px] text-gray-600 leading-relaxed ${suggestion.status === 'rejected' ? '' : ''}`}>
              {suggestion.existingProgress}
            </p>
          </div>

          {/* Suggested */}
          <div className={`rounded-lg p-4 border ${
            suggestion.status === 'approved'
              ? 'bg-green-50 border-green-200'
              : suggestion.status === 'rejected'
                ? 'bg-gray-50 border-gray-200'
                : 'bg-violet-50 border-violet-200'
          }`}>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-1.5">
                <ArrowRight className={`w-3 h-3 ${suggestion.status === 'approved' ? 'text-green-500' : 'text-violet-500'}`} />
                <span className={`text-[11px] font-semibold uppercase tracking-wider ${
                  suggestion.status === 'approved' ? 'text-green-600' : 'text-violet-600'
                }`}>
                  {suggestion.status === 'approved' ? 'Approved Update' : 'Suggested Update'}
                </span>
              </div>
              {!isDone && !isEditing && (
                <button
                  onClick={handleEdit}
                  className="text-[11px] text-gray-500 hover:text-gray-700 flex items-center gap-1 transition-colors"
                >
                  <Pencil className="w-3 h-3" />
                  Edit
                </button>
              )}
            </div>

            {isEditing ? (
              <textarea
                value={editValue}
                onChange={e => setEditValue(e.target.value)}
                className="w-full text-[13px] text-gray-800 leading-relaxed bg-white border border-violet-300 rounded-md p-2 resize-none focus:outline-none focus:ring-2 focus:ring-violet-400 focus:border-transparent"
                rows={5}
                autoFocus
              />
            ) : (
              <p className={`text-[13px] leading-relaxed ${
                suggestion.status === 'rejected' ? 'line-through text-gray-400' : 'text-gray-700'
              }`}>
                {suggestion.suggestedProgress}
              </p>
            )}
          </div>
        </div>

        {/* AI Reasoning toggle */}
        <div className="border border-gray-100 rounded-lg overflow-hidden">
          <button
            onClick={() => setShowReasoning(!showReasoning)}
            className="w-full flex items-center gap-2 px-4 py-3 hover:bg-gray-50 transition-colors text-left"
          >
            <Lightbulb className="w-3.5 h-3.5 text-amber-500 flex-shrink-0" strokeWidth={1.75} />
            <span className="text-[12.5px] font-medium text-gray-700 flex-1">AI Reasoning</span>
            {showReasoning
              ? <ChevronUp className="w-3.5 h-3.5 text-gray-400" />
              : <ChevronDown className="w-3.5 h-3.5 text-gray-400" />
            }
          </button>
          {showReasoning && (
            <div className="px-4 pb-4 bg-amber-50 border-t border-amber-100">
              <p className="text-[12.5px] text-gray-700 leading-relaxed pt-3">{suggestion.reasoning}</p>
            </div>
          )}
        </div>

        {/* Files responsible */}
        <div>
          <div className="flex items-center gap-1.5 mb-2.5">
            <FileCode className="w-3.5 h-3.5 text-gray-400" strokeWidth={1.75} />
            <h3 className="text-[12px] font-semibold text-gray-500 uppercase tracking-wider">
              Files Responsible ({suggestion.files.length})
            </h3>
          </div>
          <div className="space-y-1.5">
            {suggestion.files.map(file => (
              <div key={file.path} className="flex items-center gap-3 bg-gray-50 rounded-md px-3 py-2">
                <span className={`text-[10.5px] font-bold uppercase flex-shrink-0 px-1.5 py-0.5 rounded ${
                  file.type === 'added' ? 'bg-green-100 text-green-700' :
                  file.type === 'deleted' ? 'bg-red-100 text-red-700' :
                  'bg-gray-200 text-gray-600'
                }`}>
                  {file.type === 'added' ? '+' : file.type === 'deleted' ? '-' : 'M'}
                </span>
                <span className="font-mono text-[12px] text-gray-700 flex-1 truncate">{file.path}</span>
                <span className="font-mono text-[11px] text-gray-400 flex-shrink-0">{file.changes}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Actions */}
        {!isDone && (
          <div className="flex items-center gap-3 pt-2 border-t border-gray-100">
            {isEditing && (
              <button
                onClick={() => setIsEditing(false)}
                className="text-[13px] text-gray-500 hover:text-gray-700 px-3 py-2 transition-colors"
              >
                Cancel
              </button>
            )}
            <button
              onClick={handleReject}
              disabled={loading !== null}
              className="flex items-center gap-1.5 px-4 py-2 rounded-md border border-gray-200 text-[13px] font-medium text-gray-600 hover:bg-gray-100 hover:border-gray-300 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <XCircle className="w-4 h-4" strokeWidth={1.75} />
              {loading === 'reject' ? 'Rejecting…' : 'Reject'}
            </button>
            <button
              onClick={handleApprove}
              disabled={loading !== null}
              className="flex items-center gap-1.5 ml-auto px-5 py-2 rounded-md bg-[#16A34A] text-white text-[13px] font-semibold hover:bg-[#15803d] active:bg-[#14532d] transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-sm hover:shadow-md"
              style={{ transform: 'scale(1)', transition: 'transform 150ms ease, box-shadow 150ms ease' }}
              onMouseEnter={e => (e.currentTarget.style.transform = 'scale(1.01)')}
              onMouseLeave={e => (e.currentTarget.style.transform = 'scale(1)')}
            >
              {isEditing ? <Send className="w-4 h-4" strokeWidth={2} /> : <CheckCircle2 className="w-4 h-4" strokeWidth={2} />}
              {loading === 'approve' ? 'Approving…' : isEditing ? 'Approve with Edits' : 'Approve Update'}
            </button>
          </div>
        )}

        {suggestion.status === 'approved' && (
          <div className="flex items-center gap-2 pt-2 border-t border-green-100 text-green-600">
            <CheckCircle2 className="w-4 h-4" strokeWidth={2} />
            <span className="text-[13px] font-medium">Approved — syncing to Notion workspace</span>
          </div>
        )}
      </div>
    </div>
  )
}
