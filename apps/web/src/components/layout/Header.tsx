'use client'

import { useState } from 'react'
import { Bell, Search, Plus, X, Check, CheckCheck } from 'lucide-react'
import { useAuth } from '@/providers/AuthProvider'
import { cn } from '@/lib/utils'
import Link from 'next/link'

interface Notification {
  id: string
  title: string
  body: string
  read: boolean
  time: string
}

interface HeaderProps {
  title?: string
  actions?: React.ReactNode
  notifications?: Notification[]
}

export default function Header({ title, actions, notifications = [] }: HeaderProps) {
  const { user } = useAuth()
  const [showNotifications, setShowNotifications] = useState(false)
  const [localNotifs, setLocalNotifs] = useState(notifications)

  const unread = localNotifs.filter((n) => !n.read).length

  const markAllRead = () => {
    setLocalNotifs((prev) => prev.map((n) => ({ ...n, read: true })))
  }

  return (
    <header className="app-header bg-white border-b border-gray-100 flex items-center px-6 gap-4">
      {/* Title */}
      <div className="flex-1 min-w-0">
        {title && (
          <h1 className="text-sm font-semibold text-gray-900 truncate">{title}</h1>
        )}
      </div>

      {/* Actions slot */}
      {actions && <div className="flex items-center gap-2">{actions}</div>}

      {/* Right controls */}
      <div className="flex items-center gap-1">
        {/* Notifications */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications((v) => !v)}
            className={cn(
              'relative w-8 h-8 flex items-center justify-center rounded-lg transition-colors',
              showNotifications ? 'bg-gray-100 text-gray-900' : 'text-gray-400 hover:bg-gray-50 hover:text-gray-700',
            )}
          >
            <Bell className="w-4 h-4" />
            {unread > 0 && (
              <span className="absolute top-1 right-1 w-2 h-2 bg-[#0F62FE] rounded-full" />
            )}
          </button>

          {showNotifications && (
            <>
              <div
                className="fixed inset-0 z-40"
                onClick={() => setShowNotifications(false)}
              />
              <div className="absolute right-0 top-10 w-80 bg-white border border-gray-200 rounded-xl shadow-xl z-50 fade-in overflow-hidden">
                <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
                  <span className="text-sm font-semibold text-gray-900">Notifications</span>
                  <div className="flex items-center gap-1">
                    {unread > 0 && (
                      <button
                        onClick={markAllRead}
                        className="flex items-center gap-1 text-xs text-gray-400 hover:text-[#0F62FE] transition-colors px-2 py-1 rounded"
                      >
                        <CheckCheck className="w-3 h-3" />
                        Mark all read
                      </button>
                    )}
                    <button
                      onClick={() => setShowNotifications(false)}
                      className="p-1 text-gray-400 hover:text-gray-700 rounded"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
                <div className="max-h-72 overflow-y-auto">
                  {localNotifs.length === 0 ? (
                    <div className="py-10 text-center">
                      <Bell className="w-6 h-6 text-gray-300 mx-auto mb-2" />
                      <p className="text-sm text-gray-400">No notifications</p>
                    </div>
                  ) : (
                    localNotifs.map((n) => (
                      <div
                        key={n.id}
                        className={cn(
                          'px-4 py-3 border-b border-gray-50 last:border-0 hover:bg-gray-50 transition-colors',
                          !n.read && 'bg-blue-50/40',
                        )}
                        onClick={() =>
                          setLocalNotifs((prev) =>
                            prev.map((x) => (x.id === n.id ? { ...x, read: true } : x)),
                          )
                        }
                      >
                        <div className="flex items-start gap-2">
                          {!n.read && <span className="w-1.5 h-1.5 bg-[#0F62FE] rounded-full mt-1.5 flex-shrink-0" />}
                          <div className={cn('flex-1', n.read && 'pl-3.5')}>
                            <p className="text-xs font-medium text-gray-900">{n.title}</p>
                            <p className="text-xs text-gray-500 mt-0.5">{n.body}</p>
                            <p className="text-[10px] text-gray-400 mt-1">{n.time}</p>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </>
          )}
        </div>

        {/* User avatar */}
        {user && (
          <Link href="/settings" className="ml-1">
            {user.avatar_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={user.avatar_url}
                alt={user.github_username}
                className="w-7 h-7 rounded-full border border-gray-200 hover:border-gray-400 transition-colors"
              />
            ) : (
              <div className="w-7 h-7 rounded-full bg-blue-100 flex items-center justify-center text-xs font-bold text-blue-700">
                {(user.name || user.github_username || '?')[0].toUpperCase()}
              </div>
            )}
          </Link>
        )}
      </div>
    </header>
  )
}
