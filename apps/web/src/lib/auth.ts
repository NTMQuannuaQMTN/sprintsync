/**
 * Client-side auth utilities. Session state itself lives in Supabase's
 * client (see lib/supabase.ts) — this module just adapts it to the app's
 * own User/profile shape via the backend's /auth/me.
 */
'use client'

import { supabase } from './supabase'
import { authApi } from './api'
import type { User } from './types'

export async function isAuthenticated(): Promise<boolean> {
  const { data } = await supabase.auth.getSession()
  return !!data.session
}

export async function fetchCurrentUser(): Promise<User | null> {
  const authed = await isAuthenticated()
  if (!authed) return null
  try {
    return await authApi.getMe()
  } catch {
    return null
  }
}

export async function signOut() {
  await supabase.auth.signOut()
  window.location.href = '/login'
}
