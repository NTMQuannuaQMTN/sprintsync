'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/providers/AuthProvider'
import Sidebar from './Sidebar'
import Header from './Header'

interface AppShellProps {
  children: React.ReactNode
  headerTitle?: string
  headerActions?: React.ReactNode
  pendingSuggestions?: number
  repoId?: string | null
  repoName?: string | null
}

export default function AppShell({
  children,
  headerTitle,
  headerActions,
  pendingSuggestions = 0,
  repoId,
  repoName,
}: AppShellProps) {
  const { user, loading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!loading && !user) {
      router.replace('/login')
    }
  }, [user, loading, router])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F8F9FA]">
        <div className="flex items-center gap-3 text-gray-400">
          <div className="w-4 h-4 border-2 border-gray-300 border-t-[#0F62FE] rounded-full animate-spin" />
          <span className="text-sm">Loading…</span>
        </div>
      </div>
    )
  }

  if (!user) return null

  return (
    <div>
      <Sidebar
        pendingSuggestions={pendingSuggestions}
        repoId={repoId}
        repoName={repoName}
      />
      <Header title={headerTitle} actions={headerActions} />
      <main className="app-main">
        {children}
      </main>
    </div>
  )
}
