'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AlertCircle } from 'lucide-react'
import { supabase } from '@/lib/supabase'
import { authApi } from '@/lib/api'

/**
 * Post-login handshake. This is where login/page.tsx's
 * supabase.auth.signInWithOAuth({ redirectTo }) lands after GitHub hands
 * control back to Supabase and Supabase redirects here with a `?code=...`
 * (PKCE flow — see lib/supabase.ts).
 *
 * This page is the ONLY place that ever calls exchangeCodeForSession():
 * lib/supabase.ts sets `detectSessionInUrl: false` specifically so the SDK
 * never tries to do this automatically. Two exchange attempts for the same
 * code always fails the second time (PKCE codes are single-use — see
 * CHECKLIST.md BUG-010) and relying on the SDK's automatic path swallows
 * the real error entirely (getSession() awaits the same init step but
 * discards its result, always surfacing a generic "no session" no matter
 * what actually went wrong — see BUG-009). Doing the exchange explicitly,
 * exactly once, is what actually surfaces a diagnosable error message.
 *
 * Responsibilities, in order:
 *  1. Exchange the `code` for a real session.
 *  2. Hand the GitHub provider_token to our backend (POST /auth/sync) —
 *     Supabase only includes it on this initial exchange, never again, so
 *     this is the one place in the app that can ever capture it.
 *  3. Send the user on to /onboarding (if their profile has no display
 *     name yet — common, since GitHub accounts frequently don't set a
 *     public full name) or straight to /dashboard.
 */
export default function AuthCallbackPage() {
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)
  // Guards against React Strict Mode's dev-only double-invoke of effects —
  // a second exchange attempt for the same code always fails, since the
  // code (and its verifier) are single-use.
  const ranRef = useRef(false)

  useEffect(() => {
    if (ranRef.current) return
    ranRef.current = true

    let active = true

    const run = async () => {
      const params = new URLSearchParams(window.location.search)
      const urlError = params.get('error_description') || params.get('error')
      if (urlError) {
        setError(urlError)
        return
      }

      const code = params.get('code')
      if (!code) {
        setError(
          'No authorization code in the redirect URL. Check Supabase dashboard > ' +
            'Authentication > URL Configuration > Redirect URLs includes exactly ' +
            `${window.location.origin}/auth/callback.`,
        )
        return
      }

      const { data, error: exchangeError } = await supabase.auth.exchangeCodeForSession(code)
      if (!active) return

      if (exchangeError || !data.session) {
        setError(exchangeError?.message || 'Could not establish a session after sign-in.')
        return
      }

      let profile = null
      if (data.session.provider_token) {
        try {
          profile = await authApi.syncProviderToken(data.session.provider_token)
        } catch {
          // Non-fatal: land the user in the app regardless. Repository
          // listing/connecting will surface a clear error if the token
          // never made it through, instead of blocking sign-in on it.
        }
      }
      if (!profile) {
        try {
          profile = await authApi.getMe()
        } catch {
          // Fall through — still send them into the app; AppShell/AuthProvider
          // will sort out auth state from here.
        }
      }

      router.replace(profile && !profile.name ? '/onboarding' : '/dashboard')
    }

    run()
    return () => {
      active = false
    }
  }, [router])

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F8F9FA] p-6">
        <div className="max-w-sm w-full bg-white border border-gray-200 rounded-xl p-6 text-center">
          <div className="w-10 h-10 bg-rose-50 rounded-full flex items-center justify-center mx-auto mb-3">
            <AlertCircle className="w-5 h-5 text-rose-500" />
          </div>
          <h1 className="text-sm font-semibold text-gray-900 mb-1">Sign-in failed</h1>
          <p className="text-xs text-gray-500 mb-4">{error}</p>
          <a
            href="/login"
            className="inline-flex items-center justify-center px-4 py-2 bg-gray-900 text-white text-xs rounded-lg hover:bg-gray-800 transition-colors font-medium"
          >
            Back to login
          </a>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#F8F9FA]">
      <div className="flex items-center gap-3 text-gray-400">
        <div className="w-4 h-4 border-2 border-gray-300 border-t-[#0F62FE] rounded-full animate-spin" />
        <span className="text-sm">Signing you in…</span>
      </div>
    </div>
  )
}
