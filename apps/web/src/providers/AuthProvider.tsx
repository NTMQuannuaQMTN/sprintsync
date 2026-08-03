'use client'

import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import type { User } from '@/lib/types'
import { fetchCurrentUser, signOut } from '@/lib/auth'
import { supabase } from '@/lib/supabase'

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

// /auth/callback owns the post-OAuth handshake (session detection, syncing
// the GitHub provider token) — it must never get bounced to /login by the
// !u redirect below while that's still in flight.
const PUBLIC_PATHS = ['/', '/login', '/auth/callback']

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
    let active = true

    const init = async () => {
      const u = await fetchCurrentUser()
      if (!active) return
      setUser(u)
      setLoading(false)

      if (!u && !PUBLIC_PATHS.includes(pathname)) {
        router.replace('/login')
      }
    }
    init()

    const { data: subscription } = supabase.auth.onAuthStateChange(async (event) => {
      if (event === 'SIGNED_OUT') {
        setUser(null)
        if (!PUBLIC_PATHS.includes(pathname)) router.replace('/login')
        return
      }
      const u = await fetchCurrentUser()
      setUser(u)
    })

    return () => {
      active = false
      subscription.subscription.unsubscribe()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname, router])

  const logout = useCallback(() => {
    setUser(null)
    void signOut()
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
