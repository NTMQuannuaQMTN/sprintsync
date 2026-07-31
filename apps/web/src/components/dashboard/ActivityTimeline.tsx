import { GitCommit, Brain, FileText, CheckCircle, RefreshCw } from 'lucide-react'
import { NotionIcon } from '@/components/ui/NotionIcon'
import { GitHubIcon } from '@/components/ui/GitHubIcon'
import { formatTimeAgo } from '@/lib/utils'
import type { ActivityEvent } from '@/lib/types'

interface ActivityTimelineProps {
  events: ActivityEvent[]
}

function EventIcon({ type }: { type: ActivityEvent['type'] }) {
  const configs = {
    commit_received: { bg: 'bg-gray-100', el: <GitHubIcon className="w-4 h-4 text-[#24292f]" /> },
    ai_analyzed: { bg: 'bg-blue-50', el: <Brain className="w-4 h-4 text-blue-600" strokeWidth={1.75} /> },
    suggestion_created: { bg: 'bg-violet-50', el: <FileText className="w-4 h-4 text-violet-600" strokeWidth={1.75} /> },
    user_approved: { bg: 'bg-green-50', el: <CheckCircle className="w-4 h-4 text-green-600" strokeWidth={1.75} /> },
    notion_synced: { bg: 'bg-gray-100', el: <NotionIcon className="w-4 h-4" /> },
  }
  const config = configs[type]
  return (
    <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${config.bg}`}>
      {config.el}
    </div>
  )
}

export function ActivityTimeline({ events }: ActivityTimelineProps) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-green-500 rounded-full agent-pulse" />
          <h2 className="text-[14px] font-semibold text-gray-900">Activity Timeline</h2>
        </div>
        <span className="text-[12px] text-gray-400">{events.length} events</span>
      </div>

      <div className="p-5">
        <div className="relative">
          <div className="absolute left-[15px] top-4 bottom-4 w-px bg-gray-100" />
          <div className="space-y-1">
            {events.map((event, i) => (
              <div key={event.id} className="flex items-start gap-4">
                <div className="relative z-10">
                  <EventIcon type={event.type} />
                </div>
                <div className={`flex-1 min-w-0 pt-1 ${i < events.length - 1 ? 'pb-4' : ''}`}>
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <p className="text-[13px] font-semibold text-gray-800">{event.title}</p>
                      <p className="text-[12px] text-gray-500 leading-relaxed mt-0.5">{event.description}</p>
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {event.type === 'commit_received' && event.metadata.hash && (
                          <span className="font-mono text-[10.5px] text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">
                            {String(event.metadata.hash)}
                          </span>
                        )}
                        {event.type === 'ai_analyzed' && event.metadata.confidence && (
                          <span className="text-[10.5px] text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded font-medium">
                            {String(event.metadata.confidence)}% confidence
                          </span>
                        )}
                        {event.type === 'ai_analyzed' && event.metadata.filesAnalyzed && (
                          <span className="text-[10.5px] text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">
                            {String(event.metadata.filesAnalyzed)} files
                          </span>
                        )}
                        {event.type === 'suggestion_created' && event.metadata.taskId && (
                          <span className="text-[10.5px] text-violet-600 bg-violet-50 px-1.5 py-0.5 rounded font-medium">
                            {String(event.metadata.taskId)}
                          </span>
                        )}
                        {event.type === 'notion_synced' && event.metadata.syncDuration && (
                          <span className="text-[10.5px] text-green-600 bg-green-50 px-1.5 py-0.5 rounded font-medium">
                            {String(event.metadata.syncDuration)}
                          </span>
                        )}
                      </div>
                    </div>
                    <span className="text-[11px] text-gray-400 whitespace-nowrap flex-shrink-0">
                      {formatTimeAgo(event.timestamp)}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
