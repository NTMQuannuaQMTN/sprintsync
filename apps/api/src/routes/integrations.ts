import { Router } from 'express'
import { mockRepo, mockNotionWorkspace } from '../data/mockData'

const router = Router()

const integrations = [
  {
    id: 'int-001',
    provider_type: 'github',
    provider_category: 'repository',
    name: mockRepo.fullName,
    status: 'active',
    external_id: mockRepo.id,
    connected_at: '2026-06-01T08:00:00Z',
    last_synced_at: new Date(Date.now() - 1000 * 60 * 14).toISOString(),
    metadata: {
      repo_url: mockRepo.url,
      language: mockRepo.language,
      stars: mockRepo.stars,
      private: mockRepo.private,
    },
  },
  {
    id: 'int-002',
    provider_type: 'notion',
    provider_category: 'project',
    name: mockNotionWorkspace.name,
    status: 'active',
    external_id: mockNotionWorkspace.id,
    connected_at: mockNotionWorkspace.connectedAt,
    last_synced_at: new Date(Date.now() - 1000 * 60 * 89).toISOString(),
    metadata: {
      workspace_url: mockNotionWorkspace.url,
      icon: mockNotionWorkspace.icon,
    },
  },
  {
    id: 'int-003',
    provider_type: 'jira',
    provider_category: 'project',
    name: 'Acme Jira',
    status: 'inactive',
    external_id: null,
    connected_at: null,
    last_synced_at: null,
    metadata: {},
  },
  {
    id: 'int-004',
    provider_type: 'linear',
    provider_category: 'project',
    name: 'Linear',
    status: 'inactive',
    external_id: null,
    connected_at: null,
    last_synced_at: null,
    metadata: {},
  },
  {
    id: 'int-005',
    provider_type: 'gitlab',
    provider_category: 'repository',
    name: 'GitLab',
    status: 'inactive',
    external_id: null,
    connected_at: null,
    last_synced_at: null,
    metadata: {},
  },
]

router.get('/', (_req, res) => {
  res.json(integrations)
})

router.get('/:id', (req, res) => {
  const integration = integrations.find(i => i.id === req.params.id)
  if (!integration) {
    res.status(404).json({ error: 'Integration not found' })
    return
  }
  res.json(integration)
})

router.post('/:id/sync', (req, res) => {
  const integration = integrations.find(i => i.id === req.params.id)
  if (!integration) {
    res.status(404).json({ error: 'Integration not found' })
    return
  }
  res.json({
    success: true,
    message: `Sync triggered for ${integration.name}`,
    synced_at: new Date().toISOString(),
  })
})

export default router
