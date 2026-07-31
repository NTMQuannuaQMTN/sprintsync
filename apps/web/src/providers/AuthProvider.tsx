'use client'

import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import type { User } from '@/lib/types'
import { fetchCurrentUser, handleAuthCallback, isAuthenticated, signOut } from '@/lib/auth'

interface AuthContext {
  user: User | null
  loading: boolean
  logout: () => void
  refresh: () => Promise<void>
}

const AuthCtx = createContext<AuthContext>({
  user: null,
  loading: true,
  logout: () => {},
  refresh: async () => {},
})

const PUBLIC_PATHS = ['/', '/login']

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()
  const pathname = usePathname()

  const refresh = useCallback(async () => {
    const u = await fetchCurrentUser()
    setUser(u)
  }, [])

  useEffect(() => {
    const init = async () => {
      // Handle OAuth callback token in URL
      handleAuthCallback()

      const u = await fetchCurrentUser()
      setUser(u)
      setLoading(false)

      if (!u && !PUBLIC_PATHS.includes(pathname)) {
        router.replace('/login')
      }
    }
    init()
  }, [pathname, router])

  const logout = useCallback(() => {
    setUser(null)
    signOut()
  }, [])

  return (
    <AuthCtx.Provider value={{ user, loading, logout, refresh }}>
      {children}
    </AuthCtx.Provider>
  )
}

export function useAuth() {
  return useContext(AuthCtx)
}
