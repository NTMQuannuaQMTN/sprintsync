'use client'

import { useState } from 'react'
import AppShell from '@/components/layout/AppShell'
import { useAuth } from '@/providers/AuthProvider'
import { Settings, User, Bell, Shield, Cpu, Palette, ChevronRight } from 'lucide-react'

type Section = 'profile' | 'notifications' | 'security' | 'ai' | 'appearance'

const sections: { id: Section; label: string; icon: typeof Settings; description: string }[] = [
  { id: 'profile',       label: 'Profile',       icon: User,       description: 'Your account details' },
  { id: 'notifications', label: 'Notifications', icon: Bell,       description: 'Alert preferences' },
  { id: 'security',      label: 'Security',      icon: Shield,     description: 'Password and 2FA' },
  { id: 'ai',            label: 'AI Settings',   icon: Cpu,        description: 'Agent behavior and thresholds' },
  { id: 'appearance',    label: 'Appearance',    icon: Palette,    description: 'Theme and display' },
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

function NotificationsSection() {
  const prefs = [
    { label: 'New AI Suggestion', description: 'When AI generates a documentation suggestion', defaultChecked: true },
    { label: 'Suggestion Approved', description: 'When a team member approves a suggestion', defaultChecked: true },
    { label: 'Sync Completed', description: 'When Notion sync finishes', defaultChecked: false },
    { label: 'Agent Error', description: 'When the AI agent encounters an error', defaultChecked: true },
    { label: 'Weekly Report', description: 'Weekly summary of AI activity', defaultChecked: false },
  ]
  return (
    <div>
      <h2 className="text-[15px] font-semibold text-gray-900 mb-4">Notification Preferences</h2>
      <div className="space-y-3">
        {prefs.map(pref => (
          <label key={pref.label} className="flex items-start gap-3 p-4 bg-white border border-gray-200 rounded-lg cursor-pointer hover:border-gray-300 transition-colors">
            <input type="checkbox" defaultChecked={pref.defaultChecked} className="mt-0.5 w-4 h-4 accent-gray-900" />
            <div>
              <p className="text-[13px] font-medium text-gray-800">{pref.label}</p>
              <p className="text-[12px] text-gray-500">{pref.description}</p>
            </div>
          </label>
        ))}
      </div>
    </div>
  )
}

function AISection() {
  return (
    <div>
      <h2 className="text-[15px] font-semibold text-gray-900 mb-4">AI Agent Settings</h2>
      <div className="space-y-5">
        <div className="p-4 bg-white border border-gray-200 rounded-lg">
          <label className="block text-[13px] font-semibold text-gray-700 mb-1">Auto-Apply Threshold</label>
          <p className="text-[12px] text-gray-500 mb-3">Automatically apply suggestions above this confidence score without manual review.</p>
          <div className="flex items-center gap-3">
            <input type="range" min={70} max={99} defaultValue={95} className="flex-1 accent-gray-900" />
            <span className="text-[13px] font-semibold text-gray-700 w-10 text-right">95%</span>
          </div>
        </div>

        <div className="p-4 bg-white border border-gray-200 rounded-lg">
          <label className="block text-[13px] font-semibold text-gray-700 mb-1">Analysis Model</label>
          <p className="text-[12px] text-gray-500 mb-3">AI model used for commit analysis and documentation generation.</p>
          <select className="px-3 py-2 text-[13px] border border-gray-200 rounded-lg bg-white focus:outline-none focus:border-gray-400 transition-colors">
            <option value="sprintsync-ai-v2">SprintSync AI v2 (default)</option>
            <option value="sprintsync-ai-v1">SprintSync AI v1</option>
          </select>
        </div>

        <div className="p-4 bg-white border border-gray-200 rounded-lg">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[13px] font-semibold text-gray-700">Sync Frequency</p>
              <p className="text-[12px] text-gray-500 mt-0.5">How often the agent syncs repository activity</p>
            </div>
            <select className="px-3 py-2 text-[13px] border border-gray-200 rounded-lg bg-white focus:outline-none focus:border-gray-400 transition-colors">
              <option>Every 15 minutes</option>
              <option>Every 30 minutes</option>
              <option>Every hour</option>
              <option>On push only</option>
            </select>
          </div>
        </div>

        <div className="p-4 bg-white border border-gray-200 rounded-lg">
          <label className="flex items-center justify-between cursor-pointer">
            <div>
              <p className="text-[13px] font-semibold text-gray-700">Skip Merge Commits</p>
              <p className="text-[12px] text-gray-500 mt-0.5">Do not analyze merge commits</p>
            </div>
            <input type="checkbox" defaultChecked className="w-4 h-4 accent-gray-900" />
          </label>
        </div>
      </div>
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

function AppearanceSection() {
  return (
    <div>
      <h2 className="text-[15px] font-semibold text-gray-900 mb-4">Appearance</h2>
      <div className="space-y-4">
        <div className="p-4 bg-white border border-gray-200 rounded-lg">
          <p className="text-[13px] font-semibold text-gray-700 mb-3">Theme</p>
          <div className="flex gap-3">
            {[
              { label: 'Light', active: true },
              { label: 'Dark', active: false },
              { label: 'System', active: false },
            ].map(({ label, active }) => (
              <button
                key={label}
                className={`px-4 py-2 text-[13px] font-medium rounded-lg border transition-colors ${
                  active ? 'bg-gray-900 text-white border-gray-900' : 'bg-white text-gray-600 border-gray-200 hover:border-gray-300'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
        <div className="p-4 bg-white border border-gray-200 rounded-lg">
          <label className="flex items-center justify-between cursor-pointer">
            <div>
              <p className="text-[13px] font-semibold text-gray-700">Compact Mode</p>
              <p className="text-[12px] text-gray-500 mt-0.5">Reduce spacing for more content density</p>
            </div>
            <input type="checkbox" className="w-4 h-4 accent-gray-900" />
          </label>
        </div>
      </div>
    </div>
  )
}

type SectionProps = { user: ReturnType<typeof useAuth>['user'] }

const sectionComponents: Record<Section, React.FC<SectionProps>> = {
  profile:       ProfileSection,
  notifications: NotificationsSection,
  security:      SecuritySection,
  ai:            AISection,
  appearance:    AppearanceSection,
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
