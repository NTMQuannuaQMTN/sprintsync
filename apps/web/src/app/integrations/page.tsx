import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
import { Plug, CheckCircle2, AlertCircle, Circle, RefreshCw, ExternalLink } from 'lucide-react'
import { GitHubIcon } from '@/components/ui/GitHubIcon'
import { NotionIcon } from '@/components/ui/NotionIcon'
import { fetchDashboard, fetchIntegrations } from '@/lib/api'
import { formatTimeAgo } from '@/lib/utils'

interface Integration {
  id: string
  provider_type: string
  provider_category: string
  name: string
  status: 'active' | 'inactive' | 'error' | 'pending'
  external_id: string | null
  connected_at: string | null
  last_synced_at: string | null
  metadata: Record<string, unknown>
}

function ProviderIcon({ type, className }: { type: string; className?: string }) {
  if (type === 'github') return <GitHubIcon className={className} />
  if (type === 'notion') return <NotionIcon className={className} />
  return <Plug className={className} />
}

const providerMeta: Record<string, { label: string; description: string; color: string }> = {
  github:     { label: 'GitHub',     description: 'Code repositories and commit tracking', color: '#24292f' },
  notion:     { label: 'Notion',     description: 'Project management and documentation',  color: '#000000' },
  jira:       { label: 'Jira',       description: 'Issue tracking and project management', color: '#0052CC' },
  linear:     { label: 'Linear',     description: 'Modern issue and project tracking',     color: '#5E6AD2' },
  gitlab:     { label: 'GitLab',     description: 'Git repository management',             color: '#FC6D26' },
  clickup:    { label: 'ClickUp',    description: 'All-in-one project management',         color: '#7B68EE' },
  confluence: { label: 'Confluence', description: 'Wiki and knowledge management',         color: '#172B4D' },
}

export default async function IntegrationsPage() {
  const [dashboard, integrations] = await Promise.all([
    fetchDashboard(),
    fetchIntegrations(),
  ])

  const active   = (integrations as Integration[]).filter(i => i.status === 'active')
  const inactive = (integrations as Integration[]).filter(i => i.status !== 'active')

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col ml-[240px] min-w-0">
        <Header
          repoFullName={dashboard.repo.fullName}
          repoBranch={dashboard.repo.currentBranch}
          notionWorkspace={dashboard.notionWorkspace.name}
          agentStatus={dashboard.agentStatus.status}
        />
        <main className="flex-1 overflow-y-auto pt-[60px]">
          <div className="p-6 max-w-[1440px] mx-auto">
            <div className="mb-6">
              <h1 className="text-[20px] font-bold text-gray-900">Integrations</h1>
              <p className="text-[13px] text-gray-500 mt-0.5">Connect your tools to enable AI-powered synchronization</p>
            </div>

            {/* Active integrations */}
            <section className="mb-8">
              <h2 className="text-[13px] font-semibold text-gray-500 uppercase tracking-wider mb-3">
                Connected ({active.length})
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {active.map((integration) => {
                  const meta = providerMeta[integration.provider_type] ?? { label: integration.provider_type, description: '', color: '#666' }
                  return (
                    <div key={integration.id} className="bg-white border border-gray-200 rounded-xl p-5 hover:border-gray-300 transition-colors">
                      <div className="flex items-start gap-4">
                        <div className="w-10 h-10 rounded-lg bg-gray-50 border border-gray-200 flex items-center justify-center flex-shrink-0">
                          <ProviderIcon type={integration.provider_type} className="w-5 h-5" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-0.5">
                            <span className="text-[14px] font-semibold text-gray-900">{meta.label}</span>
                            <span className="text-[10px] font-medium text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded capitalize">
                              {integration.provider_category}
                            </span>
                            <CheckCircle2 className="w-3.5 h-3.5 text-green-500 ml-auto flex-shrink-0" strokeWidth={2} />
                          </div>
                          <p className="text-[12px] text-gray-500 mb-3">{integration.name}</p>
                          <div className="flex items-center gap-3 text-[11px] text-gray-400">
                            {integration.connected_at && (
                              <span>Connected {formatTimeAgo(integration.connected_at)}</span>
                            )}
                            {integration.last_synced_at && (
                              <span className="flex items-center gap-1">
                                <RefreshCw className="w-3 h-3" />
                                Synced {formatTimeAgo(integration.last_synced_at)}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 mt-4 pt-4 border-t border-gray-100">
                        <button className="flex items-center gap-1.5 text-[12px] text-gray-600 hover:text-gray-900 font-medium transition-colors">
                          <RefreshCw className="w-3 h-3" strokeWidth={2} />
                          Sync Now
                        </button>
                        <button className="flex items-center gap-1.5 text-[12px] text-gray-600 hover:text-gray-900 font-medium transition-colors ml-auto">
                          <ExternalLink className="w-3 h-3" strokeWidth={2} />
                          Configure
                        </button>
                        <button className="text-[12px] text-red-500 hover:text-red-700 font-medium transition-colors ml-3">
                          Disconnect
                        </button>
                      </div>
                    </div>
                  )
                })}
              </div>
            </section>

            {/* Available integrations */}
            <section>
              <h2 className="text-[13px] font-semibold text-gray-500 uppercase tracking-wider mb-3">
                Available ({inactive.length})
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {inactive.map((integration) => {
                  const meta = providerMeta[integration.provider_type] ?? { label: integration.provider_type, description: '', color: '#666' }
                  return (
                    <div key={integration.id} className="bg-white border border-gray-200 rounded-xl p-5 border-dashed opacity-70 hover:opacity-100 hover:border-solid hover:border-gray-300 transition-all">
                      <div className="flex items-start gap-4">
                        <div className="w-10 h-10 rounded-lg bg-gray-50 border border-gray-200 flex items-center justify-center flex-shrink-0">
                          <ProviderIcon type={integration.provider_type} className="w-5 h-5 opacity-50" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-0.5">
                            <span className="text-[14px] font-semibold text-gray-700">{meta.label}</span>
                            <Circle className="w-3.5 h-3.5 text-gray-300 ml-auto flex-shrink-0" strokeWidth={2} />
                          </div>
                          <p className="text-[12px] text-gray-400 mb-3">{meta.description}</p>
                        </div>
                      </div>
                      <button className="w-full mt-2 py-2 text-[13px] font-medium text-gray-700 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-lg transition-colors">
                        Connect {meta.label}
                      </button>
                    </div>
                  )
                })}
              </div>
            </section>
          </div>
        </main>
      </div>
    </div>
  )
}
