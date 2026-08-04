'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { GitBranch, ArrowRight, Loader2 } from 'lucide-react'
import { useAuth } from '@/providers/AuthProvider'
import { authApi } from '@/lib/api'

/**
 * One-time post-signup step. GitHub accounts frequently have no public
 * display name set (raw_user_meta_data ->> 'full_name' is empty), so the
 * auth.users -> profiles trigger leaves `profiles.name` null for a lot of
 * real sign-ups. apps/web/src/app/auth/callback/page.tsx routes here
 * instead of /dashboard the first time that's the case.
 */
export default function OnboardingPage() {
  const router = useRouter()
  const { user, loading, refresh } = useAuth()
  const [name, setName] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Already has a name (e.g. navigated back here manually after finishing
  // onboarding) — nothing to do here.
  if (!loading && user?.name) {
    router.replace('/dashboard')
    return null
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) return

    setSubmitting(true)
    setError(null)
    try {
      await authApi.updateName(trimmed)
      await refresh()
      router.replace('/dashboard')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save your name.')
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#F8F9FA] p-6">
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-2 mb-8 justify-center">
          <div className="w-8 h-8 bg-[#0F62FE] rounded-lg flex items-center justify-center">
            <GitBranch className="w-4 h-4 text-white" />
          </div>
          <span className="font-semibold text-gray-900">SprintSync AI</span>
        </div>

        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <h1 className="text-lg font-bold text-gray-900 mb-1">What should we call you?</h1>
          <p className="text-sm text-gray-500 mb-5">
            GitHub didn't give us a display name{user?.github_username ? ` for @${user.github_username}` : ''} — add one to finish setting up your account.
          </p>

          <form onSubmit={handleSubmit}>
            <input
              autoFocus
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={user?.github_username || 'Your name'}
              className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2.5 mb-3 focus:outline-none focus:ring-2 focus:ring-[#0F62FE]/20 focus:border-[#0F62FE]"
            />

            {error && <p className="text-xs text-rose-600 mb-3">{error}</p>}

            <button
              type="submit"
              disabled={!name.trim() || submitting}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-gray-900 text-white text-sm rounded-lg hover:bg-gray-800 transition-colors font-medium disabled:opacity-50"
            >
              {submitting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  Continue
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
