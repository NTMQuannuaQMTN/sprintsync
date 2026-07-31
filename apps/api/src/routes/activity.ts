import { Router } from 'express'
import { mockActivity } from '../data/mockData'

const router = Router()

router.get('/', (_req, res) => {
  res.json(mockActivity)
})

export default router
