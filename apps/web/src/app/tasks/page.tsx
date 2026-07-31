import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
import { CheckSquare, AlertOctagon, Clock, CheckCircle2, Circle } from 'lucide-react'
import { fetchDashboard, fetchTasks } from '@/lib/api'
import { formatTimeAgo } from '@/lib/utils'

const statusConfig = {
  in_progress: { label: 'In Progress', icon: Clock, color: 'text-blue-600', bg: 'bg-blue-50', dot: 'bg-blue-500' },
  completed:   { label: 'Completed',   icon: CheckCircle2, color: 'text-green-600', bg: 'bg-green-50', dot: 'bg-green-500' },
  open:        { label: 'Open',        icon: Circle, color: 'text-gray-600', bg: 'bg-gray-100', dot: 'bg-gray-400' },
  blocked:     { label: 'Blocked',     icon: AlertOctagon, color: 'text-red-600', bg: 'bg-red-50', dot: 'bg-red-500' },
} as const

type TaskStatus = keyof typeof statusConfig

export default async function TasksPage() {
  const [dashboard, data] = await Promise.all([
    fetchDashboard(),
    fetchTasks(),
  ])

  const { tasks, sprint, summary } = data

  const grouped: Record<TaskStatus, typeof tasks> = {
    in_progress: tasks.filter((t: { status: string }) => t.status === 'in_progress'),
    open:        tasks.filter((t: { status: string }) => t.status === 'open'),
    blocked:     tasks.filter((t: { status: string }) => t.status === 'blocked'),
    completed:   tasks.filter((t: { status: string }) => t.status === 'completed'),
  }

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
            {/* Header */}
            <div className="mb-6 flex items-center justify-between">
              <div>
                <h1 className="text-[20px] font-bold text-gray-900">Tasks</h1>
                <p className="text-[13px] text-gray-500 mt-0.5">
                  {sprint.name} · {sprint.completionPercentage}% complete
                </p>
              </div>
            </div>

            {/* Sprint progress bar */}
            <div className="bg-white border border-gray-200 rounded-xl p-5 mb-6">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <span className="text-[14px] font-semibold text-gray-900">{sprint.name}</span>
                  <span className="ml-2 text-[12px] text-gray-400">{sprint.startDate} → {sprint.endDate}</span>
                </div>
                <span className="text-[13px] font-semibold text-gray-700">{sprint.completedPoints} / {sprint.totalPoints} pts</span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-2">
                <div
                  className="bg-gray-900 h-2 rounded-full transition-all"
                  style={{ width: `${sprint.completionPercentage}%` }}
                />
              </div>
              {/* Summary pills */}
              <div className="flex items-center gap-3 mt-3">
                {(Object.entries(summary) as [string, number][])
                  .filter(([k]) => k !== 'total')
                  .map(([key, count]) => {
                    const cfg = statusConfig[key as TaskStatus]
                    if (!cfg) return null
                    const Icon = cfg.icon
                    return (
                      <span key={key} className={`flex items-center gap-1 text-[12px] font-medium ${cfg.color} ${cfg.bg} px-2.5 py-1 rounded-full`}>
                        <Icon className="w-3 h-3" strokeWidth={2} />
                        {count} {cfg.label}
                      </span>
                    )
                  })}
              </div>
            </div>

            {/* Kanban columns */}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
              {((['in_progress', 'open', 'blocked', 'completed'] as TaskStatus[])).map(status => {
                const cfg = statusConfig[status]
                const Icon = cfg.icon
                const columnTasks = grouped[status]
                return (
                  <div key={status} className="bg-gray-50 rounded-xl p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <Icon className={`w-4 h-4 ${cfg.color}`} strokeWidth={1.75} />
                      <span className="text-[13px] font-semibold text-gray-700">{cfg.label}</span>
                      <span className="ml-auto text-[11px] font-semibold bg-white border border-gray-200 text-gray-500 rounded-full px-1.5 py-0.5">{columnTasks.length}</span>
                    </div>
                    <div className="space-y-2">
                      {columnTasks.map((task: {
                        id: string
                        title: string
                        status: string
                        assignee: string
                        updatedAt: string
                        points: number
                        blockedReason?: string
                      }) => (
                        <div key={task.id} className="bg-white border border-gray-200 rounded-lg p-3 shadow-sm hover:border-gray-300 transition-colors">
                          <div className="flex items-start justify-between gap-2 mb-1.5">
                            <span className="text-[11px] font-mono text-gray-400">{task.id}</span>
                            {task.points > 0 && (
                              <span className="text-[10px] font-semibold text-gray-500 bg-gray-100 rounded px-1.5 py-0.5">{task.points}p</span>
                            )}
                          </div>
                          <p className="text-[12.5px] font-medium text-gray-800 leading-snug mb-2">{task.title}</p>
                          {task.blockedReason && (
                            <p className="text-[11px] text-red-600 bg-red-50 rounded px-2 py-1 mb-2 leading-snug">{task.blockedReason}</p>
                          )}
                          <div className="flex items-center justify-between">
                            <span className="text-[11px] text-gray-400">{task.assignee.split(' ')[0]}</span>
                            <span className="text-[11px] text-gray-400">{formatTimeAgo(task.updatedAt)}</span>
                          </div>
                        </div>
                      ))}
                      {columnTasks.length === 0 && (
                        <div className="text-center py-6 text-[12px] text-gray-400">No tasks</div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}
