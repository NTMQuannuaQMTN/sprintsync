import { Router } from 'express'
import { mockTeamProgress } from '../data/mockData'

const router = Router()

// Flatten all task-like items from team progress into a unified task list
const tasks = [
  ...mockTeamProgress.recentlyUpdated.map(t => ({ ...t, type: 'sprint' })),
  ...mockTeamProgress.blockedTasks.map(t => ({
    id: t.id,
    title: t.title,
    status: 'blocked' as const,
    assignee: t.assignee,
    updatedAt: t.blockedSince,
    points: 0,
    blockedReason: t.reason,
    type: 'sprint',
  })),
]

router.get('/', (_req, res) => {
  res.json({
    tasks,
    sprint: mockTeamProgress.sprint,
    summary: mockTeamProgress.tasks,
  })
})

router.get('/:id', (req, res) => {
  const task = tasks.find(t => t.id === req.params.id)
  if (!task) {
    res.status(404).json({ error: 'Task not found' })
    return
  }
  res.json(task)
})

export default router
