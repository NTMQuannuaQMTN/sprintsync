'use client'

import { CheckSquare, AlertTriangle, Clock, Target } from 'lucide-react'
import { RadialBarChart, RadialBar, PolarAngleAxis, ResponsiveContainer } from 'recharts'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { formatTimeAgo } from '@/lib/utils'
import type { TeamProgress } from '@/lib/types'

interface TeamProgressPanelProps {
  data: TeamProgress
}

export function TeamProgressPanel({ data }: TeamProgressPanelProps) {
  const { sprint, tasks, recentlyUpdated, blockedTasks } = data
  const sprintData = [{ value: sprint.completionPercentage, fill: '#111827' }]
  const rawDaysLeft = Math.ceil((new Date(sprint.endDate).getTime() - Date.now()) / (1000 * 60 * 60 * 24))
  const daysLeft = Math.max(0, rawDaysLeft)

  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Target className="w-4 h-4 text-gray-700" strokeWidth={1.75} />
          <h2 className="text-[14px] font-semibold text-gray-900">Team Progress</h2>
        </div>
        <span className="text-[12px] font-medium text-gray-500">{sprint.name}</span>
      </div>

      <div className="p-5 space-y-5">
        {/* Sprint ring */}
        <div className="flex items-center gap-5">
          <div className="relative w-24 h-24 flex-shrink-0">
            <ResponsiveContainer width="100%" height="100%">
              <RadialBarChart
                innerRadius="70%"
                outerRadius="100%"
                data={sprintData}
                startAngle={90}
                endAngle={90 - 360 * (sprint.completionPercentage / 100)}
              >
                <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
                <RadialBar dataKey="value" cornerRadius={6} background={{ fill: '#F3F4F6' }} />
              </RadialBarChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-[20px] font-bold text-gray-900 leading-none">{sprint.completionPercentage}%</span>
              <span className="text-[10px] text-gray-400 font-medium">done</span>
            </div>
          </div>

          <div className="flex-1 space-y-2">
            <div className="flex justify-between">
              <span className="text-[12px] text-gray-500">Story Points</span>
              <span className="text-[13px] font-semibold text-gray-800">{sprint.completedPoints} / {sprint.totalPoints}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[12px] text-gray-500">Days Remaining</span>
              <span className="text-[13px] font-semibold text-gray-800">{daysLeft} days</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[12px] text-gray-500">Velocity</span>
              <span className="text-[13px] font-semibold text-gray-800">{sprint.velocity} pts</span>
            </div>
          </div>
        </div>

        {/* Task counts */}
        <div className="grid grid-cols-4 gap-2">
          {[
            { label: 'Open', count: tasks.open, color: 'text-gray-700' },
            { label: 'Active', count: tasks.inProgress, color: 'text-blue-600' },
            { label: 'Done', count: tasks.completed, color: 'text-green-600' },
            { label: 'Blocked', count: tasks.blocked, color: 'text-red-600' },
          ].map(item => (
            <div key={item.label} className="bg-gray-50 rounded-lg p-2.5 text-center">
              <div className={`text-[18px] font-bold ${item.color}`}>{item.count}</div>
              <div className="text-[10px] text-gray-500 font-medium mt-0.5">{item.label}</div>
            </div>
          ))}
        </div>

        {/* Recently Updated */}
        <div>
          <div className="flex items-center gap-1.5 mb-2.5">
            <Clock className="w-3.5 h-3.5 text-gray-400" strokeWidth={1.75} />
            <h3 className="text-[12px] font-semibold text-gray-500 uppercase tracking-wider">Recently Updated</h3>
          </div>
          <div>
            {recentlyUpdated.slice(0, 4).map((task, i) => (
              <div
                key={task.id}
                className={`flex items-center gap-2.5 py-2 ${i < 3 ? 'border-b border-gray-50' : ''}`}
              >
                <CheckSquare
                  className={`w-3.5 h-3.5 flex-shrink-0 ${task.status === 'completed' ? 'text-green-500' : 'text-gray-300'}`}
                  strokeWidth={2}
                />
                <div className="flex-1 min-w-0">
                  <p className="text-[12.5px] text-gray-800 truncate">{task.title}</p>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <StatusBadge status={task.status} />
                  <span className="text-[11px] text-gray-400">{formatTimeAgo(task.updatedAt)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Blocked tasks */}
        {blockedTasks.length > 0 && (
          <div>
            <div className="flex items-center gap-1.5 mb-2.5">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-500" strokeWidth={2} />
              <h3 className="text-[12px] font-semibold text-amber-600 uppercase tracking-wider">Blocked</h3>
            </div>
            <div className="space-y-2">
              {blockedTasks.map(task => (
                <div key={task.id} className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[12.5px] font-semibold text-gray-800">{task.id}</span>
                    <span className="text-[11px] text-amber-600 font-medium">{formatTimeAgo(task.blockedSince)}</span>
                  </div>
                  <p className="text-[12px] text-gray-700 mb-1">{task.title}</p>
                  <p className="text-[11px] text-amber-700 leading-snug">{task.reason}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
