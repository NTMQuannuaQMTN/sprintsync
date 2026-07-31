import { Router } from 'express'
import { mockAgentStatus, mockCommits, mockPullRequests, mockRepoHealth, mockTeamProgress, mockRepo, mockNotionWorkspace } from '../data/mockData'

const router = Router()

router.get('/', (_req, res) => {
  res.json({
    repo: mockRepo,
    notionWorkspace: mockNotionWorkspace,
    agentStatus: mockAgentStatus,
    recentCommits: mockCommits,
    pullRequests: mockPullRequests,
    repoHealth: mockRepoHealth,
    teamProgress: mockTeamProgress,
  })
})

export default router
