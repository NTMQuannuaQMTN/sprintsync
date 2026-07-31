import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
import { Activity, GitCommit, Brain, Sparkles, CheckCircle2, RefreshCw } from 'lucide-react'
import { fetchDashboard, fetchActivity } from '@/lib/api'
import { formatTimeAgo } from '@/lib/utils'
import type { ActivityEvent } from '@/lib/types'

const eventConfig = {
  commit_received:    { icon: GitCommit,    color: 'text-gray-600',   bg: 'bg-gray-100',   label: 'Commit' },
  ai_analyzed:        { icon: Brain,        color: 'text-violet-600', bg: 'bg-violet-50',  label: 'AI Analysis' },
  suggestion_created: { icon: Sparkles,     color: 'text-blue-600',   bg: 'bg-blue-50',    label: 'Suggestion' },
  user_approved:      { icon: CheckCircle2, color: 'text-green-600',  bg: 'bg-green-50',   label: 'Approved' },
  notion_synced:      { icon: RefreshCw,    color: 'text-indigo-600', bg: 'bg-indigo-50',  label: 'Synced' },
} as const

type EventType = keyof typeof eventConfig

export default async function ActivityPage() {
  const [dashboard, events] = await Promise.all([
    fetchDashboard(),
    fetchActivity(),
  ])

  // Group events by day
  const grouped: Record<string, ActivityEvent[]> = {}
  for (const event of events as ActivityEvent[]) {
    const date = new Date(event.timestamp).toLocaleDateString('en-US', {
      weekday: 'long', month: 'long', day: 'numeric',
    })
    if (!grouped[date]) grouped[date] = []
    grouped[date].push(event)
  }

  const typeCounts = (events as ActivityEvent[]).reduce<Record<string, number>>((acc, e) => {
    acc[e.type] = (acc[e.type] || 0) + 1
    return acc
  }, {})

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
              <h1 className="text-[20px] font-bold text-gray-900">Activity</h1>
              <p className="text-[13px] text-gray-500 mt-0.5">Full audit trail of all SprintSync AI actions</p>
            </div>

            {/* Event type filter pills */}
            <div className="flex flex-wrap items-center gap-2 mb-6">
              <span className="text-[12px] font-semibold text-gray-500 mr-1">Filter:</span>
              {(Object.entries(eventConfig) as [EventType, typeof eventConfig[EventType]][]).map(([type, cfg]) => {
                const Icon = cfg.icon
                const count = typeCounts[type] ?? 0
                return (
                  <div key={type} className={`flex items-center gap-1.5 text-[12px] font-medium px-2.5 py-1 rounded-full border border-gray-200 ${cfg.bg} ${cfg.color}`}>
                    <Icon className="w-3 h-3" strokeWidth={2} />
                    {cfg.label}
                    {count > 0 && <span className="font-bold">{count}</span>}
                  </div>
                )
              })}
            </div>

            {/* Timeline */}
            <div className="space-y-8">
              {Object.entries(grouped).map(([date, dayEvents]) => (
                <div key={date}>
                  <div className="flex items-center gap-3 mb-4">
                    <Activity className="w-3.5 h-3.5 text-gray-400" strokeWidth={1.75} />
                    <span className="text-[12px] font-semibold text-gray-500 uppercase tracking-wide">{date}</span>
                    <div className="flex-1 h-px bg-gray-100" />
                    <span className="text-[11px] text-gray-400">{dayEvents.length} events</span>
                  </div>

                  <div className="relative ml-2">
                    {/* Vertical line */}
                    <div className="absolute left-[13px] top-0 bottom-0 w-px bg-gray-100" />

                    <div className="space-y-1">
                      {dayEvents.map((event) => {
                        const cfg = eventConfig[event.type as EventType] ?? eventConfig.commit_received
                        const Icon = cfg.icon
                        return (
                          <div key={event.id} className="flex items-start gap-3 py-2 group">
                            {/* Icon dot */}
                            <div className={`relative z-10 w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 ${cfg.bg} border border-gray-200`}>
                              <Icon className={`w-3.5 h-3.5 ${cfg.color}`} strokeWidth={2} />
                            </div>

                            {/* Content */}
                            <div className="flex-1 min-w-0 bg-white border border-gray-200 rounded-lg px-4 py-3 hover:border-gray-300 transition-colors">
                              <div className="flex items-center justify-between gap-2 mb-0.5">
                                <span className="text-[13px] font-semibold text-gray-800">{event.title}</span>
                                <span className="text-[11px] text-gray-400 flex-shrink-0">{formatTimeAgo(event.timestamp)}</span>
                              </div>
                              <p className="text-[12.5px] text-gray-500 leading-relaxed">{event.description}</p>
                              {Object.keys(event.metadata).length > 0 && (
                                <div className="flex flex-wrap gap-2 mt-2">
                                  {Object.entries(event.metadata).slice(0, 3).map(([k, v]) => (
                                    <span key={k} className="text-[10px] font-mono text-gray-400 bg-gray-50 border border-gray-100 px-1.5 py-0.5 rounded">
                                      {k}: {String(v)}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}
