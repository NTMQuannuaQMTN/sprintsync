/**
 * Client-side auth utilities — token storage and user context.
 */
'use client'

import { getToken, setToken, clearToken, authApi } from './api'
import type { User } from './types'

export { getToken, setToken, clearToken }

export function isAuthenticated(): boolean {
  return !!getToken()
}

export async function fetchCurrentUser(): Promise<User | null> {
  if (!isAuthenticated()) return null
  try {
    return await authApi.getMe()
  } catch {
    clearToken()
    return null
  }
}

export function signOut() {
  clearToken()
  window.location.href = '/login'
}

/** Called on /dashboard?token=xxx after GitHub OAuth callback */
export function handleAuthCallback(): string | null {
  if (typeof window === 'undefined') return null
  const params = new URLSearchParams(window.location.search)
  const token = params.get('token')
  if (token) {
    setToken(token)
    // Clean URL
    const url = new URL(window.location.href)
    url.searchParams.delete('token')
    window.history.replaceState({}, '', url.toString())
    return token
  }
  return null
}
