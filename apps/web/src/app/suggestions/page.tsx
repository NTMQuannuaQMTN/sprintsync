import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
import { SuggestedDocUpdate } from '@/components/dashboard/SuggestedDocUpdate'
import { Sparkles, CheckCircle2, XCircle, Clock } from 'lucide-react'
import { fetchDashboard, fetchSuggestions } from '@/lib/api'
import type { Suggestion } from '@/lib/types'

export default async function SuggestionsPage() {
  const [dashboard, suggestions] = await Promise.all([
    fetchDashboard(),
    fetchSuggestions(),
  ])

  const pending  = suggestions.filter((s: Suggestion) => s.status === 'pending')
  const approved = suggestions.filter((s: Suggestion) => s.status === 'approved')
  const rejected = suggestions.filter((s: Suggestion) => s.status === 'rejected')

  const total = suggestions.length
  const approvalRate = total > 0
    ? Math.round((approved.length / (approved.length + rejected.length || 1)) * 100)
    : 0

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col ml-[240px] min-w-0">
        <Header
          repoFullName={dashboard.repo.fullName}
          repoBranch={dashboard.repo.currentBranch}
          notionWorkspace={dashboard.notionWorkspace.name}
          agentStatus={dashboard.agentStatus.status}
        />
        <main className="flex-1 overflow-y-auto pt-[60px]">
          <div className="p-6 max-w-[1440px] mx-auto">
            <div className="mb-6">
              <h1 className="text-[20px] font-bold text-gray-900">AI Suggestions</h1>
              <p className="text-[13px] text-gray-500 mt-0.5">Review and approve AI-generated documentation updates</p>
            </div>

            {/* Stats row */}
            <div className="grid grid-cols-4 gap-4 mb-6">
              {[
                { label: 'Total', value: total, icon: Sparkles, color: 'text-gray-700', bg: 'bg-gray-50' },
                { label: 'Pending Review', value: pending.length, icon: Clock, color: 'text-yellow-700', bg: 'bg-yellow-50' },
                { label: 'Approved', value: approved.length, icon: CheckCircle2, color: 'text-green-700', bg: 'bg-green-50' },
                { label: 'Rejected', value: rejected.length, icon: XCircle, color: 'text-red-700', bg: 'bg-red-50' },
              ].map(({ label, value, icon: Icon, color, bg }) => (
                <div key={label} className={`${bg} border border-gray-200 rounded-xl p-4`}>
                  <div className="flex items-center gap-2 mb-1">
                    <Icon className={`w-4 h-4 ${color}`} strokeWidth={1.75} />
                    <span className={`text-[12px] font-semibold ${color}`}>{label}</span>
                  </div>
                  <div className="text-[24px] font-bold text-gray-900">{value}</div>
                </div>
              ))}
            </div>

            {approvalRate > 0 && (
              <div className="mb-5 bg-blue-50 border border-blue-200 rounded-xl px-5 py-3 flex items-center gap-3">
                <span className="text-[13px] text-blue-800 font-medium">
                  Overall approval rate: <strong>{approvalRate}%</strong> · {approved.length} approved of {approved.length + rejected.length} reviewed
                </span>
              </div>
            )}

            {/* Pending suggestions */}
            {pending.length > 0 && (
              <section className="mb-6">
                <h2 className="text-[13px] font-semibold text-gray-500 uppercase tracking-wider mb-3">
                  Awaiting Review ({pending.length})
                </h2>
                <div className="space-y-4">
                  {pending.map((s: Suggestion) => (
                    <SuggestedDocUpdate key={s.id} suggestion={s} />
                  ))}
                </div>
              </section>
            )}

            {/* Approved */}
            {approved.length > 0 && (
              <section className="mb-6">
                <h2 className="text-[13px] font-semibold text-gray-500 uppercase tracking-wider mb-3">
                  Approved ({approved.length})
                </h2>
                <div className="space-y-3">
                  {approved.map((s: Suggestion) => (
                    <div key={s.id} className="bg-white border border-gray-200 rounded-xl p-4 flex items-center gap-3 opacity-75">
                      <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0" strokeWidth={2} />
                      <div className="flex-1 min-w-0">
                        <p className="text-[13px] font-semibold text-gray-800 truncate">{s.relatedTask.title}</p>
                        <p className="text-[12px] text-gray-500 truncate">{s.relatedTask.id}</p>
                      </div>
                      <span className="text-[11px] text-green-600 font-semibold bg-green-50 px-2 py-0.5 rounded-full">Approved</span>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Rejected */}
            {rejected.length > 0 && (
              <section>
                <h2 className="text-[13px] font-semibold text-gray-500 uppercase tracking-wider mb-3">
                  Rejected ({rejected.length})
                </h2>
                <div className="space-y-3">
                  {rejected.map((s: Suggestion) => (
                    <div key={s.id} className="bg-white border border-gray-200 rounded-xl p-4 flex items-center gap-3 opacity-60">
                      <XCircle className="w-4 h-4 text-red-400 flex-shrink-0" strokeWidth={2} />
                      <div className="flex-1 min-w-0">
                        <p className="text-[13px] font-semibold text-gray-800 truncate">{s.relatedTask.title}</p>
                        <p className="text-[12px] text-gray-500 truncate">{s.relatedTask.id}</p>
                      </div>
                      <span className="text-[11px] text-red-600 font-semibold bg-red-50 px-2 py-0.5 rounded-full">Rejected</span>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {suggestions.length === 0 && (
              <div className="text-center py-16 text-gray-400">
                <Sparkles className="w-8 h-8 mx-auto mb-3 opacity-30" strokeWidth={1.5} />
                <p className="text-[14px] font-medium">No suggestions yet</p>
                <p className="text-[13px]">Push a commit to GitHub to trigger AI analysis</p>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}
