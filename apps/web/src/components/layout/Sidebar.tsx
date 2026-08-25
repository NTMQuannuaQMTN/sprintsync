'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  GitBranch,
  LayoutDashboard,
  FolderGit2,
  CheckSquare,
  Sparkles,
  Activity,
  GitCommit,
  Settings,
  LogOut,
  Radar,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuth } from '@/providers/AuthProvider'

const NAV = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/repositories', label: 'Repositories', icon: FolderGit2 },
]

interface SidebarProps {
  pendingSuggestions?: number
  repoId?: string | null
  repoName?: string | null
}

export default function Sidebar({ pendingSuggestions = 0, repoId, repoName }: SidebarProps) {
  const pathname = usePathname()
  const { user, logout } = useAuth()

  const repoNav = repoId
    ? [
        { href: `/repositories/${repoId}`, label: 'Overview', icon: FolderGit2 },
        { href: `/repositories/${repoId}/tasks`, label: 'Tasks', icon: CheckSquare },
        { href: `/repositories/${repoId}/commits`, label: 'Commits', icon: GitCommit },
        {
          href: `/repositories/${repoId}/suggestions`,
          label: 'Suggestions',
          icon: Sparkles,
          badge: pendingSuggestions,
        },
        { href: `/repositories/${repoId}/activity`, label: 'Activity', icon: Activity },
        { href: `/repositories/${repoId}/intelligence`, label: 'Intelligence', icon: Radar },
      ]
    : []

  return (
    <aside className="app-sidebar flex flex-col bg-white border-r border-gray-100">
      {/* Logo */}
      <div className="h-[60px] flex items-center gap-2.5 px-5 border-b border-gray-100">
        <div className="w-7 h-7 bg-[#0F62FE] rounded-md flex items-center justify-center flex-shrink-0">
          <GitBranch className="w-3.5 h-3.5 text-white" />
        </div>
        <span className="font-semibold text-gray-900 text-sm tracking-tight">SprintSync AI</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4 px-3">
        {/* Main nav */}
        <div className="space-y-0.5">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(href + '/')
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                  active
                    ? 'bg-blue-50 text-[#0F62FE] font-medium'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900',
                )}
              >
                <Icon className="w-4 h-4 flex-shrink-0" />
                {label}
              </Link>
            )
          })}
        </div>

        {/* Repo sub-nav */}
        {repoNav.length > 0 && (
          <div className="mt-6">
            <div className="px-3 mb-2">
              <p className="text-[10px] font-medium text-gray-400 uppercase tracking-widest truncate">
                {repoName || 'Repository'}
              </p>
            </div>
            <div className="space-y-0.5">
              {repoNav.map(({ href, label, icon: Icon, badge }) => {
                const active = pathname === href
                return (
                  <Link
                    key={href}
                    href={href}
                    className={cn(
                      'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                      active
                        ? 'bg-blue-50 text-[#0F62FE] font-medium'
                        : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900',
                    )}
                  >
                    <Icon className="w-4 h-4 flex-shrink-0" />
                    <span className="flex-1">{label}</span>
                    {badge !== undefined && badge > 0 && (
                      <span className="min-w-[18px] h-[18px] flex items-center justify-center bg-[#0F62FE] text-white text-[10px] font-medium rounded-full px-1">
                        {badge > 99 ? '99+' : badge}
                      </span>
                    )}
                  </Link>
                )
              })}
            </div>
          </div>
        )}
      </nav>

      {/* Footer */}
      <div className="border-t border-gray-100 p-3 space-y-0.5">
        <Link
          href="/settings"
          className={cn(
            'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
            pathname === '/settings'
              ? 'bg-blue-50 text-[#0F62FE] font-medium'
              : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900',
          )}
        >
          <Settings className="w-4 h-4" />
          Settings
        </Link>

        {user && (
          <div className="flex items-center gap-3 px-3 py-2 mt-1">
            {user.avatar_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={user.avatar_url}
                alt={user.github_username}
                className="w-6 h-6 rounded-full flex-shrink-0"
              />
            ) : (
              <div className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center text-[10px] font-bold text-blue-700 flex-shrink-0">
                {(user.name || user.github_username || '?')[0].toUpperCase()}
              </div>
            )}
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-gray-900 truncate">
                {user.name || user.github_username}
              </p>
              <p className="text-[10px] text-gray-400 truncate">@{user.github_username}</p>
            </div>
            <button
              onClick={logout}
              className="text-gray-400 hover:text-gray-700 transition-colors"
              title="Sign out"
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>
    </aside>
  )
}
