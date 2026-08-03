'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AlertCircle } from 'lucide-react'
import { supabase } from '@/lib/supabase'
import { authApi } from '@/lib/api'

/**
 * Post-login handshake. This is where login/page.tsx's
 * supabase.auth.signInWithOAuth({ redirectTo }) lands after GitHub hands
 * control back to Supabase and Supabase redirects here with a session.
 *
 * Responsibilities, in order:
 *  1. Let supabase-js finish parsing the session out of the redirect URL.
 *  2. Hand the GitHub provider_token to our backend (POST /auth/sync) —
 *     Supabase only includes it on this initial redirect, never again, so
 *     this is the one place in the app that can ever capture it.
 *  3. Send the user on to the dashboard.
 *
 * Surfaces a real error state instead of bouncing to /login silently —
 * Supabase can redirect here with ?error=...&error_description=... (e.g.
 * "provider is not enabled") which is far more useful shown to the user
 * than swallowed.
 */
export default function AuthCallbackPage() {
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true

    const run = async () => {
      const params = new URLSearchParams(window.location.search)
      const urlError = params.get('error_description') || params.get('error')
      if (urlError) {
        setError(urlError)
        return
      }

      // supabase-js already exchanges a PKCE `code` (or parses an implicit
      // hash token) automatically as part of its own initialization, the
      // first time any auth method is called on this client — getSession()
      // triggers and awaits that. Do NOT also call
      // exchangeCodeForSession(code) manually here "just in case": PKCE
      // codes are single-use, and the automatic exchange already consumes
      // the stored code_verifier, so a second manual attempt reliably fails
      // with "PKCE code verifier not found in storage" even though the
      // first (automatic) exchange may have succeeded just fine.
      const { data, error: sessionError } = await supabase.auth.getSession()

      if (!active) return

      if (sessionError || !data.session) {
        const hasCode = Boolean(params.get('code'))
        const hasHashToken = window.location.hash.includes('access_token')
        setError(
          (sessionError?.message || 'Could not establish a session after sign-in.') +
            ` (redirect had ${hasCode ? 'a code param' : hasHashToken ? 'a hash token' : 'no auth params at all'} —` +
            ' if this keeps happening, check Supabase dashboard > Authentication > URL Configuration > Redirect URLs' +
            ` includes exactly ${window.location.origin}/auth/callback)`,
        )
        return
      }

      if (data.session.provider_token) {
        try {
          await authApi.syncProviderToken(data.session.provider_token)
        } catch {
          // Non-fatal: land the user in the app regardless. Repository
          // listing/connecting will surface a clear error if the token
          // never made it through, instead of blocking sign-in on it.
        }
      }

      router.replace('/dashboard')
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
