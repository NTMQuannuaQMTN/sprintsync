import Link from 'next/link'
import { GitBranch, Zap, CheckCircle2, ArrowRight, Github, Sparkles, GitCommit, Bell } from 'lucide-react'

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-white">
      {/* Nav */}
      <nav className="border-b border-gray-100 sticky top-0 bg-white/90 backdrop-blur-sm z-10">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-[#0F62FE] rounded-md flex items-center justify-center">
              <GitBranch className="w-4 h-4 text-white" />
            </div>
            <span className="font-semibold text-gray-900 tracking-tight">SprintSync AI</span>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/login" className="text-sm text-gray-500 hover:text-gray-900 transition-colors">
              Sign in
            </Link>
            <Link
              href="/login"
              className="px-4 py-1.5 bg-[#0F62FE] text-white text-sm rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              Get started
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-6 pt-24 pb-20">
        <div className="max-w-3xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-blue-50 text-blue-700 text-xs font-medium rounded-full mb-6 border border-blue-100">
            <Sparkles className="w-3 h-3" />
            AI-powered engineering operations
          </div>
          <h1 className="text-5xl font-bold text-gray-900 leading-tight mb-6 tracking-tight">
            Your GitHub pushes,{' '}
            <span className="text-[#0F62FE]">automatically synced</span>{' '}
            to your task board
          </h1>
          <p className="text-xl text-gray-500 mb-10 leading-relaxed">
            SprintSync AI watches your commits, understands what changed, and suggests which
            tasks to mark complete. Stop manually updating project progress.
          </p>
          <div className="flex items-center gap-4">
            <Link
              href="/login"
              className="inline-flex items-center gap-2 px-6 py-3 bg-[#0F62FE] text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              <Github className="w-4 h-4" />
              Continue with GitHub
              <ArrowRight className="w-4 h-4" />
            </Link>
            <span className="text-sm text-gray-400">Free during beta · No credit card</span>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="border-t border-gray-100 bg-gray-50">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <h2 className="text-2xl font-bold text-gray-900 mb-12 text-center">How it works</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            {[
              {
                icon: <Github className="w-5 h-5" />,
                step: '01',
                title: 'Connect Repository',
                desc: 'Link your GitHub repo in one click. SprintSync installs a webhook automatically.',
              },
              {
                icon: <GitBranch className="w-5 h-5" />,
                step: '02',
                title: 'Upload Spec',
                desc: 'Upload your project specification PDF or DOCX. AI extracts implementation tasks.',
              },
              {
                icon: <GitCommit className="w-5 h-5" />,
                step: '03',
                title: 'Push Code',
                desc: 'Developers push commits as normal. SprintSync receives and analyzes each push.',
              },
              {
                icon: <Bell className="w-5 h-5" />,
                step: '04',
                title: 'Review Suggestions',
                desc: 'AI suggests which tasks are done. One click to approve and update status.',
              },
            ].map((item) => (
              <div key={item.step} className="relative">
                <div className="w-10 h-10 bg-white border border-gray-200 rounded-xl flex items-center justify-center text-gray-400 mb-4 shadow-sm">
                  {item.icon}
                </div>
                <div className="absolute top-3 left-10 font-mono text-xs text-gray-300 pl-2">
                  {item.step}
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">{item.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-6xl mx-auto px-6 py-20">
        <h2 className="text-2xl font-bold text-gray-900 mb-12 text-center">Built for engineering teams</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            {
              title: 'Confidence scoring',
              desc: 'Every AI suggestion comes with a confidence score and evidence — affected files, matching keywords, commit patterns.',
              color: 'bg-blue-50',
            },
            {
              title: 'Human in the loop',
              desc: 'AI never changes tasks without approval. You review each suggestion and approve or reject with one click.',
              color: 'bg-emerald-50',
            },
            {
              title: 'Extensible integrations',
              desc: 'Built to support Notion, Jira, Linear, ClickUp, and Confluence in future versions with minimal code changes.',
              color: 'bg-purple-50',
            },
          ].map((f) => (
            <div key={f.title} className={`${f.color} rounded-2xl p-6 border border-white`}>
              <CheckCircle2 className="w-5 h-5 text-gray-400 mb-4" />
              <h3 className="font-semibold text-gray-900 mb-2">{f.title}</h3>
              <p className="text-sm text-gray-600 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-gray-100 bg-gray-900">
        <div className="max-w-6xl mx-auto px-6 py-20 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">Ready to sync your sprints?</h2>
          <p className="text-gray-400 mb-8">Connect your GitHub in seconds.</p>
          <Link
            href="/login"
            className="inline-flex items-center gap-2 px-6 py-3 bg-white text-gray-900 rounded-lg hover:bg-gray-100 transition-colors font-medium"
          >
            <Github className="w-4 h-4" />
            Sign in with GitHub
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-100 bg-white">
        <div className="max-w-6xl mx-auto px-6 py-6 flex items-center justify-between text-sm text-gray-400">
          <span>© 2024 SprintSync AI</span>
          <span className="font-mono text-xs">v1.0.0-beta</span>
        </div>
      </footer>
    </main>
  )
}
