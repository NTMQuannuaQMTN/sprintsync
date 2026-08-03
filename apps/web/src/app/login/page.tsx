'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { GitBranch, Zap, Shield, ArrowRight } from 'lucide-react'
import { isAuthenticated } from '@/lib/auth'
import { supabase } from '@/lib/supabase'
import { GitHubIcon } from '@/components/ui/GitHubIcon'

export default function LoginPage() {
  const router = useRouter()

  useEffect(() => {
    isAuthenticated().then((authed) => {
      if (authed) router.replace('/dashboard')
    })
  }, [router])

  const handleLogin = () => {
    supabase.auth.signInWithOAuth({
      provider: 'github',
      options: {
        scopes: 'read:user user:email repo',
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    })
  }

  return (
    <div className="min-h-screen bg-white flex">
      {/* Left panel — brand */}
      <div className="hidden lg:flex lg:w-1/2 bg-gray-950 flex-col justify-between p-12">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-[#0F62FE] rounded-lg flex items-center justify-center">
            <GitBranch className="w-4 h-4 text-white" />
          </div>
          <span className="text-white font-semibold tracking-tight">SprintSync AI</span>
        </div>

        <div>
          <h1 className="text-4xl font-bold text-white leading-tight mb-6">
            Your commits,{' '}
            <span className="text-[#0F62FE]">automatically reflected</span>{' '}
            in your task board
          </h1>
          <div className="space-y-4">
            {[
              { icon: <Zap className="w-4 h-4" />, text: 'AI analyzes every commit and suggests task updates' },
              { icon: <Shield className="w-4 h-4" />, text: 'Human approval required — AI never changes tasks directly' },
              { icon: <GitBranch className="w-4 h-4" />, text: 'Connects to GitHub via webhook — zero developer overhead' },
            ].map((item, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className="mt-0.5 text-blue-400">{item.icon}</div>
                <span className="text-gray-400 text-sm leading-relaxed">{item.text}</span>
              </div>
            ))}
          </div>
        </div>

        <p className="text-gray-600 text-xs font-mono">
          SprintSync AI · Engineering Operations Platform
        </p>
      </div>

      {/* Right panel — sign in */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-sm">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-2 mb-10">
            <div className="w-8 h-8 bg-[#0F62FE] rounded-lg flex items-center justify-center">
              <GitBranch className="w-4 h-4 text-white" />
            </div>
            <span className="font-semibold text-gray-900">SprintSync AI</span>
          </div>

          <h2 className="text-2xl font-bold text-gray-900 mb-2">Sign in</h2>
          <p className="text-gray-500 text-sm mb-8">
            Connect your GitHub account to get started.
          </p>

          <button
            onClick={handleLogin}
            className="w-full flex items-center justify-center gap-3 px-4 py-3 bg-gray-900 text-white rounded-xl hover:bg-gray-800 transition-colors font-medium text-sm group"
          >
            <GitHubIcon className="w-5 h-5" />
            Continue with GitHub
            <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity -ml-1" />
          </button>

          <p className="text-center text-xs text-gray-400 mt-6">
            By signing in, you authorize SprintSync to read your repositories
            and install webhooks on repos you connect.
          </p>

          <div className="mt-10 pt-6 border-t border-gray-100">
            <p className="text-xs text-gray-400 text-center">
              Need help?{' '}
              <a href="mailto:support@sprintsync.ai" className="text-[#0F62FE] hover:underline">
                Contact support
              </a>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
