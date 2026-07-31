import express from 'express'
import cors from 'cors'
import dashboardRouter from './routes/dashboard'
import suggestionsRouter from './routes/suggestions'
import activityRouter from './routes/activity'
import reposRouter from './routes/repos'
import tasksRouter from './routes/tasks'
import integrationsRouter from './routes/integrations'
import reportsRouter from './routes/reports'

const app = express()
const PORT = process.env.PORT || 3001

app.use(cors({ origin: 'http://localhost:3000', credentials: true }))
app.use(express.json())

app.use('/api/dashboard', dashboardRouter)
app.use('/api/suggestions', suggestionsRouter)
app.use('/api/activity', activityRouter)
app.use('/api/repos', reposRouter)
app.use('/api/tasks', tasksRouter)
app.use('/api/integrations', integrationsRouter)
app.use('/api/reports', reportsRouter)

app.get('/health', (_req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() })
})

app.listen(PORT, () => {
  console.log(`SprintSync API running on http://localhost:${PORT}`)
})

export default app
