import { Router } from 'express'
import { mockSuggestions, mockActivity, mockRepoHealth, mockTeamProgress } from '../data/mockData'

const router = Router()

router.get('/', (_req, res) => {
  const approved = mockSuggestions.filter(s => s.status === 'approved').length
  const rejected = mockSuggestions.filter(s => s.status === 'rejected').length
  const pending = mockSuggestions.filter(s => s.status === 'pending').length
  const total = mockSuggestions.length

  res.json({
    period: {
      from: new Date(Date.now() - 1000 * 60 * 60 * 24 * 30).toISOString(),
      to: new Date().toISOString(),
      label: 'Last 30 days',
    },
    suggestions: {
      total,
      approved,
      rejected,
      pending,
      approval_rate: total > 0 ? Math.round((approved / (approved + rejected)) * 100) || 0 : 0,
    },
    activity: {
      total_events: mockActivity.length,
      commits_received: mockActivity.filter(a => a.type === 'commit_received').length,
      ai_analyses: mockActivity.filter(a => a.type === 'ai_analyzed').length,
      notion_syncs: mockActivity.filter(a => a.type === 'notion_synced').length,
    },
    repo_health: mockRepoHealth,
    sprint: {
      ...mockTeamProgress.sprint,
      tasks: mockTeamProgress.tasks,
      velocity_trend: [42, 48, 51, 52],
    },
    ai_performance: {
      avg_confidence: 92,
      high_confidence_rate: 78,
      avg_analysis_time_ms: 1420,
      total_tokens_used: 184200,
    },
  })
})

export default router
