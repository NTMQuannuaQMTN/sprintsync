import { Router } from 'express'
import { mockSuggestions } from '../data/mockData'

const router = Router()
const suggestions = [...mockSuggestions]

router.get('/', (_req, res) => {
  res.json(suggestions)
})

router.get('/:id', (req, res) => {
  const suggestion = suggestions.find(s => s.id === req.params.id)
  if (!suggestion) {
    res.status(404).json({ error: 'Suggestion not found' })
    return
  }
  res.json(suggestion)
})

router.post('/:id/approve', (req, res) => {
  const idx = suggestions.findIndex(s => s.id === req.params.id)
  if (idx === -1) {
    res.status(404).json({ error: 'Suggestion not found' })
    return
  }
  const editedProgress = req.body?.editedProgress
  suggestions[idx] = {
    ...suggestions[idx],
    status: 'approved',
    ...(editedProgress ? { suggestedProgress: editedProgress } : {}),
  }
  res.json({ success: true, suggestion: suggestions[idx] })
})

router.post('/:id/reject', (req, res) => {
  const idx = suggestions.findIndex(s => s.id === req.params.id)
  if (idx === -1) {
    res.status(404).json({ error: 'Suggestion not found' })
    return
  }
  suggestions[idx] = { ...suggestions[idx], status: 'rejected' }
  res.json({ success: true, suggestion: suggestions[idx] })
})

export default router
