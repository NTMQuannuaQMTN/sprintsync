'use client'

import { useEffect, useState } from 'react'
import { Brain, FileCode, RefreshCw, Zap, TrendingUp } from 'lucide-react'
import { RadialBarChart, RadialBar, ResponsiveContainer, PolarAngleAxis } from 'recharts'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { formatTimeAgo } from '@/lib/utils'
import type { AgentStatus } from '@/lib/types'

interface AIAgentPanelProps {
  agentStatus: AgentStatus
}

export function AIAgentPanel({ agentStatus: initial }: AIAgentPanelProps) {
  const [status, setStatus] = useState(initial)

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch('/api/dashboard')
        if (res.ok) {
          const data = await res.json()
          setStatus(data.agentStatus)
        }
      } catch {
        // Network error — retain previous status, will retry next tick
      }
    }, 30000)
    return () => clearInterval(interval)
  }, [])

  const confidenceData = [{ value: status.confidenceScore, fill: '#16A34A' }]
  const progressPct = Math.round((status.filesAnalyzed / status.totalFiles) * 100)

  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-gray-700" strokeWidth={1.75} />
          <h2 className="text-[14px] font-semibold text-gray-900">AI Agent</h2>
        </div>
        <StatusBadge status={status.status} dot />
      </div>

      <div className="p-5 space-y-4">
        {/* Confidence score radial */}
        <div className="flex items-center gap-4">
          <div className="relative w-24 h-24 flex-shrink-0">
            <ResponsiveContainer width="100%" height="100%">
              <RadialBarChart
                innerRadius="70%"
                outerRadius="100%"
                data={confidenceData}
                startAngle={90}
                endAngle={90 - 360 * (status.confidenceScore / 100)}
              >
                <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
                <RadialBar dataKey="value" cornerRadius={6} background={{ fill: '#F3F4F6' }} />
              </RadialBarChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-[20px] font-bold text-gray-900 leading-none">{status.confidenceScore}</span>
              <span className="text-[10px] text-gray-400 font-medium">score</span>
            </div>
          </div>
          <div className="flex-1">
            <p className="text-[13px] font-semibold text-gray-800 mb-1">Confidence Score</p>
            <p className="text-[12px] text-gray-500 leading-relaxed">
              High confidence — analysis ready for review
            </p>
            <div className="flex items-center gap-1.5 mt-2">
              <TrendingUp className="w-3 h-3 text-green-500" />
              <span className="text-[11px] font-medium text-green-600">+3 from last analysis</span>
            </div>
          </div>
        </div>

        {/* Current task */}
        <div className="bg-gray-50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-1.5 h-1.5 bg-green-500 rounded-full agent-pulse" />
            <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-wide">Currently Analyzing</span>
          </div>
          <p className="text-[12.5px] text-gray-700 leading-snug">{status.currentTask}</p>
        </div>

        {/* Files analyzed progress */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-1.5">
              <FileCode className="w-3.5 h-3.5 text-gray-400" strokeWidth={1.75} />
              <span className="text-[12px] font-medium text-gray-600">Files Analyzed</span>
            </div>
            <span className="text-[12px] font-semibold text-gray-800">
              {status.filesAnalyzed.toLocaleString()} / {status.totalFiles.toLocaleString()}
            </span>
          </div>
          <div className="w-full bg-gray-100 rounded-full h-1.5 overflow-hidden">
            <div
              className="bg-gray-900 h-1.5 rounded-full transition-all duration-700"
              style={{ width: `${progressPct}%` }}
            />
          </div>
          <div className="flex justify-between mt-1">
            <span className="text-[11px] text-gray-400">{progressPct}% complete</span>
            <span className="text-[11px] text-gray-400 font-mono">{status.model}</span>
          </div>
        </div>

        {/* Sync info */}
        <div className="grid grid-cols-2 gap-3 pt-1">
          <div className="text-center">
            <div className="flex items-center justify-center gap-1.5 mb-1">
              <RefreshCw className="w-3 h-3 text-gray-400" />
              <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-wide">Last Sync</span>
            </div>
            <p className="text-[13px] font-semibold text-gray-800">{formatTimeAgo(status.lastSync)}</p>
          </div>
          <div className="text-center">
            <div className="flex items-center justify-center gap-1.5 mb-1">
              <Zap className="w-3 h-3 text-gray-400" />
              <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-wide">Next Sync</span>
            </div>
            <p className="text-[13px] font-semibold text-gray-800">
              {(() => {
                const diff = new Date(status.nextScheduledSync).getTime() - Date.now()
                if (diff <= 0) return 'soon'
                const m = Math.round(diff / 60000)
                return m < 60 ? `in ${m}m` : `in ${Math.round(m / 60)}h`
              })()}
            </p>
          </div>
        </div>

        {/* Tokens */}
        <div className="pt-2 border-t border-gray-100 flex items-center justify-between">
          <span className="text-[12px] text-gray-400">Tokens used this session</span>
          <span className="text-[12px] font-semibold font-mono text-gray-700">{status.tokensUsed.toLocaleString()}</span>
        </div>
      </div>
    </div>
  )
}
