'use client'

import { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import type { User } from '@/lib/types'
import { fetchCurrentUser, signOut } from '@/lib/auth'
import { authApi } from '@/lib/api'
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

const PUBLIC_PATHS = ['/', '/login']

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()
  const pathname = usePathname()
  // Guards against calling /auth/sync more than once per browser tab for the
  // same provider token (onAuthStateChange can fire SIGNED_IN more than once,
  // e.g. on token refresh, and Supabase only includes provider_token on the
  // initial OAuth redirect anyway).
  const syncedTokenRef = useRef<string | null>(null)

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

    const { data: subscription } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (event === 'SIGNED_IN' && session?.provider_token && syncedTokenRef.current !== session.provider_token) {
        syncedTokenRef.current = session.provider_token
        try {
          await authApi.syncProviderToken(session.provider_token)
        } catch {
          // Non-fatal — GitHub-API-dependent endpoints will just 400 until
          // the user re-authenticates; don't block the sign-in itself on it.
        }
      }
      if (event === 'SIGNED_OUT') {
        setUser(null)
        syncedTokenRef.current = null
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
