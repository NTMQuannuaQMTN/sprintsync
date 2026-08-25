'use client'

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import AppShell from '@/components/layout/AppShell'
import { useAuth } from '@/providers/AuthProvider'
import { integrationsApi } from '@/lib/api'
import { Settings, User, Shield, Plug, ChevronRight, CheckCircle2, Loader2 } from 'lucide-react'

type Section = 'profile' | 'security' | 'integrations'

const sections: { id: Section; label: string; icon: typeof Settings; description: string }[] = [
  { id: 'profile',      label: 'Profile',      icon: User,   description: 'Your account details' },
  { id: 'security',     label: 'Security',     icon: Shield, description: 'Password and 2FA' },
  { id: 'integrations', label: 'Integrations', icon: Plug,   description: 'Task-board connections' },
]

function ProfileSection({ user }: { user: ReturnType<typeof useAuth>['user'] }) {
  const displayName = user?.name || user?.github_username || ''
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-[15px] font-semibold text-gray-900 mb-4">Profile</h2>
        <div className="flex items-center gap-4 mb-6">
          {user?.avatar_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={user.avatar_url} alt={displayName} className="w-16 h-16 rounded-full" />
          ) : (
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-violet-400 to-indigo-500 flex items-center justify-center">
              <span className="text-[18px] font-bold text-white">{displayName ? displayName[0].toUpperCase() : '?'}</span>
            </div>
          )}
          <div>
            <p className="text-[14px] font-semibold text-gray-900">{displayName}</p>
            <p className="text-[13px] text-gray-500">{user?.email || 'No public email on GitHub'}</p>
          </div>
        </div>
        <p className="text-[12px] text-gray-400 mb-4">
          Profile fields are synced from GitHub at sign-in and aren&apos;t editable here yet.
        </p>
        <div className="space-y-4">
          {[
            { label: 'Display Name', value: displayName, type: 'text' },
            { label: 'Email', value: user?.email || '', type: 'email' },
            { label: 'GitHub Username', value: user?.github_username || '', type: 'text' },
          ].map(({ label, value, type }) => (
            <div key={label}>
              <label className="block text-[12px] font-semibold text-gray-600 mb-1">{label}</label>
              <input
                type={type}
                value={value}
                readOnly
                className="w-full max-w-md px-3 py-2 text-[13px] border border-gray-200 rounded-lg bg-gray-50 text-gray-600 focus:outline-none cursor-not-allowed"
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function IntegrationsSection() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [accessToken, setAccessToken] = useState('')
  const [databaseId, setDatabaseId] = useState('')
  const [workspaceName, setWorkspaceName] = useState('')

  const { data: integrations, isLoading } = useQuery({
    queryKey: ['integrations'],
    queryFn: integrationsApi.list,
  })
  const notion = integrations?.find((i) => i.integration_type === 'notion' && i.active)

  const connectMutation = useMutation({
    mutationFn: () =>
      integrationsApi.connectNotion({
        access_token: accessToken,
        database_id: databaseId,
        workspace_name: workspaceName || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['integrations'] })
      setShowForm(false)
      setAccessToken('')
      setDatabaseId('')
      setWorkspaceName('')
    },
  })
  const disconnectMutation = useMutation({
    mutationFn: () => integrationsApi.disconnectNotion(),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['integrations'] }),
  })

  return (
    <div>
      <h2 className="text-[15px] font-semibold text-gray-900 mb-1">Task-Board Integrations</h2>
      <p className="text-[12px] text-gray-500 mb-4">
        When connected, approving an AI suggestion also mirrors the status change onto a matching
        page in your Notion database (by title lookup) — your internal task list stays the source
        of truth either way.
      </p>

      {isLoading ? (
        <div className="p-4 text-[13px] text-gray-400">Loading…</div>
      ) : notion ? (
        <div className="p-4 bg-white border border-gray-200 rounded-lg flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <div>
              <p className="text-[13px] font-semibold text-gray-700">Notion</p>
              <p className="text-[12px] text-gray-500">
                Connected{notion.workspace_name ? ` — ${notion.workspace_name}` : ''}
              </p>
            </div>
          </div>
          <button
            onClick={() => disconnectMutation.mutate()}
            disabled={disconnectMutation.isPending}
            className="text-[12px] text-red-500 hover:text-red-700 font-medium disabled:opacity-50"
          >
            {disconnectMutation.isPending ? 'Disconnecting…' : 'Disconnect'}
          </button>
        </div>
      ) : (
        <div className="p-4 bg-white border border-gray-200 rounded-lg">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[13px] font-semibold text-gray-700">Notion</p>
              <p className="text-[12px] text-gray-500 mt-0.5">Not connected</p>
            </div>
            {!showForm && (
              <button
                onClick={() => setShowForm(true)}
                className="text-[12px] text-[#0F62FE] font-medium hover:underline"
              >
                Connect
              </button>
            )}
          </div>

          {showForm && (
            <div className="mt-4 space-y-3 border-t border-gray-100 pt-4">
              <div>
                <label className="block text-[12px] font-semibold text-gray-600 mb-1">
                  Notion integration token
                </label>
                <input
                  type="password"
                  value={accessToken}
                  onChange={(e) => setAccessToken(e.target.value)}
                  placeholder="secret_..."
                  className="w-full px-3 py-2 text-[13px] border border-gray-200 rounded-lg focus:outline-none focus:border-gray-400"
                />
              </div>
              <div>
                <label className="block text-[12px] font-semibold text-gray-600 mb-1">Database ID</label>
                <input
                  value={databaseId}
                  onChange={(e) => setDatabaseId(e.target.value)}
                  placeholder="32-character Notion database id"
                  className="w-full px-3 py-2 text-[13px] border border-gray-200 rounded-lg focus:outline-none focus:border-gray-400"
                />
              </div>
              <div>
                <label className="block text-[12px] font-semibold text-gray-600 mb-1">
                  Workspace name (optional)
                </label>
                <input
                  value={workspaceName}
                  onChange={(e) => setWorkspaceName(e.target.value)}
                  className="w-full px-3 py-2 text-[13px] border border-gray-200 rounded-lg focus:outline-none focus:border-gray-400"
                />
              </div>
              {connectMutation.isError && (
                <p className="text-[12px] text-rose-600">{(connectMutation.error as Error).message}</p>
              )}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => connectMutation.mutate()}
                  disabled={connectMutation.isPending || !accessToken || !databaseId}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium bg-gray-900 text-white rounded-md hover:bg-gray-800 disabled:opacity-50"
                >
                  {connectMutation.isPending && <Loader2 className="w-3 h-3 animate-spin" />}
                  Verify &amp; connect
                </button>
                <button
                  onClick={() => setShowForm(false)}
                  className="px-3 py-1.5 text-[12px] font-medium text-gray-500 hover:text-gray-700"
                >
                  Cancel
                </button>
              </div>
              <p className="text-[11px] text-gray-400">
                Connecting makes a real request to Notion to verify the token/database before saving
                anything — a bad credential is rejected immediately.
              </p>
            </div>
          )}
        </div>
      )}

      <p className="text-[12px] text-gray-400 mt-4">
        Jira and Linear integrations are not implemented yet — the same provider abstraction supports
        adding them.
      </p>
    </div>
  )
}

function SecuritySection({ user }: { user: ReturnType<typeof useAuth>['user'] }) {
  const { logout } = useAuth()
  return (
    <div>
      <h2 className="text-[15px] font-semibold text-gray-900 mb-4">Security</h2>
      <div className="space-y-4">
        <div className="p-4 bg-white border border-gray-200 rounded-lg flex items-center justify-between">
          <div>
            <p className="text-[13px] font-semibold text-gray-700">GitHub OAuth</p>
            <p className="text-[12px] text-green-600 mt-0.5">
              {user ? `Connected as ${user.github_username}` : 'Not connected'}
            </p>
          </div>
          <button onClick={logout} className="text-[12px] text-red-500 hover:text-red-700 font-medium">
            Sign out
          </button>
        </div>
        <p className="text-[12px] text-gray-400">
          Two-factor authentication and session management are handled by GitHub — manage them from your
          GitHub account settings.
        </p>
      </div>
    </div>
  )
}

type SectionProps = { user: ReturnType<typeof useAuth>['user'] }

const sectionComponents: Record<Section, React.FC<SectionProps>> = {
  profile:      ProfileSection,
  security:     SecuritySection,
  integrations: IntegrationsSection,
}

export default function SettingsPage() {
  const [active, setActive] = useState<Section>('profile')
  const { user } = useAuth()
  const ActiveSection = sectionComponents[active]

  return (
    <AppShell headerTitle="Settings">
      <div className="p-6 max-w-[1440px] mx-auto">
        <div className="mb-6">
          <h1 className="text-[20px] font-bold text-gray-900">Settings</h1>
          <p className="text-[13px] text-gray-500 mt-0.5">Manage your account and SprintSync AI preferences</p>
        </div>

        <div className="flex gap-6">
          {/* Sidebar nav */}
          <div className="w-52 flex-shrink-0">
            <nav className="space-y-0.5">
              {sections.map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => setActive(id)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors ${
                    active === id
                      ? 'bg-gray-100 text-gray-900'
                      : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700'
                  }`}
                >
                  <Icon className="w-4 h-4 flex-shrink-0" strokeWidth={1.75} />
                  <div className="flex-1 min-w-0">
                    <p className="text-[13px] font-medium">{label}</p>
                  </div>
                  <ChevronRight className="w-3 h-3 flex-shrink-0 opacity-40" strokeWidth={2} />
                </button>
              ))}
            </nav>
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0 bg-white border border-gray-200 rounded-xl p-6">
            <ActiveSection user={user} />
          </div>
        </div>
      </div>
    </AppShell>
  )
}
