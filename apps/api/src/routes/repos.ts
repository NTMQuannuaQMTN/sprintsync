import { Router } from 'express'
import { mockRepo, mockCommits, mockPullRequests, mockRepoHealth } from '../data/mockData'

const router = Router()

router.get('/', (_req, res) => {
  res.json([
    {
      ...mockRepo,
      commits: mockCommits,
      pullRequests: mockPullRequests,
      health: mockRepoHealth,
    }
  ])
})

router.get('/:id', (req, res) => {
  if (req.params.id !== mockRepo.id) {
    res.status(404).json({ error: 'Repository not found' })
    return
  }
  res.json({ ...mockRepo, commits: mockCommits, pullRequests: mockPullRequests, health: mockRepoHealth })
})

export default router
