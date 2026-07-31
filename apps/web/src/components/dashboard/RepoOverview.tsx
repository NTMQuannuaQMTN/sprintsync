import { GitPullRequest, GitCommit, Shield, CheckCircle2, XCircle, Clock, Plus, Minus, ExternalLink } from 'lucide-react'
import { GitHubIcon } from '@/components/ui/GitHubIcon'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { formatTimeAgo } from '@/lib/utils'
import type { Commit, PullRequest, RepoHealth } from '@/lib/types'

interface RepoOverviewProps {
  commits: Commit[]
  pullRequests: PullRequest[]
  health: RepoHealth
  repoName: string
}

export function RepoOverview({ commits, pullRequests, health, repoName }: RepoOverviewProps) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <GitHubIcon className="w-4 h-4 text-[#24292f]" />
          <h2 className="text-[14px] font-semibold text-gray-900">Repository Overview</h2>
        </div>
        <a
          href={`https://github.com/${repoName}`}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-[12px] text-gray-400 hover:text-gray-700 transition-colors"
        >
          {repoName}
          <ExternalLink className="w-3 h-3" />
        </a>
      </div>

      <div className="p-5 space-y-5">
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-gray-50 rounded-lg p-3 text-center">
            <div className="text-[22px] font-bold text-gray-900">{health.score}</div>
            <div className="text-[11px] text-gray-500 mt-0.5 font-medium">Health Score</div>
          </div>
          <div className="bg-gray-50 rounded-lg p-3 text-center">
            <div className="flex items-center justify-center gap-1 text-[22px] font-bold text-gray-900">
              {health.coverage}<span className="text-[14px] font-medium text-gray-500">%</span>
            </div>
            <div className="text-[11px] text-gray-500 mt-0.5 font-medium">Coverage</div>
          </div>
          <div className="bg-gray-50 rounded-lg p-3 text-center">
            <div className="flex items-center justify-center h-[30px]">
              {health.ciStatus === 'passing' ? (
                <CheckCircle2 className="w-5 h-5 text-green-500" />
              ) : health.ciStatus === 'failing' ? (
                <XCircle className="w-5 h-5 text-red-500" />
              ) : (
                <Clock className="w-5 h-5 text-amber-500" />
              )}
            </div>
            <div className="text-[11px] text-gray-500 mt-1 font-medium capitalize">{health.ciStatus}</div>
          </div>
        </div>

        <div>
          <div className="flex items-center gap-1.5 mb-3">
            <GitCommit className="w-3.5 h-3.5 text-gray-400" strokeWidth={2} />
            <h3 className="text-[12px] font-semibold text-gray-500 uppercase tracking-wider">Recent Commits</h3>
          </div>
          <div>
            {commits.slice(0, 4).map((commit, i) => (
              <div
                key={commit.id}
                className={`flex items-start gap-3 py-2.5 ${i < 3 ? 'border-b border-gray-50' : ''}`}
              >
                <img
                  src={commit.author.avatar}
                  alt={commit.author.name}
                  className="w-6 h-6 rounded-full flex-shrink-0 mt-0.5 bg-gray-100"
                />
                <div className="flex-1 min-w-0">
                  <p className="text-[13px] text-gray-800 leading-snug line-clamp-1">{commit.message}</p>
                  <div className="flex items-center gap-2 mt-1 flex-wrap">
                    <span className="font-mono text-[11px] text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">{commit.hash}</span>
                    <span className="text-[11px] text-gray-400">{commit.author.username}</span>
                    <span className="text-[11px] text-gray-400">{formatTimeAgo(commit.timestamp)}</span>
                    <span className="text-[10px] font-medium text-green-600 flex items-center gap-0.5">
                      <Plus className="w-2.5 h-2.5" />{commit.additions}
                    </span>
                    <span className="text-[10px] font-medium text-red-500 flex items-center gap-0.5">
                      <Minus className="w-2.5 h-2.5" />{commit.deletions}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="flex items-center gap-1.5 mb-3">
            <GitPullRequest className="w-3.5 h-3.5 text-gray-400" strokeWidth={2} />
            <h3 className="text-[12px] font-semibold text-gray-500 uppercase tracking-wider">Pull Requests</h3>
            <span className="ml-auto text-[11px] text-gray-400">{pullRequests.filter(p => p.state === 'open').length} open</span>
          </div>
          <div>
            {pullRequests.slice(0, 3).map((pr, i) => (
              <div
                key={pr.id}
                className={`flex items-start gap-3 py-2.5 ${i < 2 ? 'border-b border-gray-50' : ''}`}
              >
                <GitPullRequest
                  className={`w-4 h-4 flex-shrink-0 mt-0.5 ${pr.state === 'merged' ? 'text-violet-500' : pr.state === 'open' ? 'text-green-500' : 'text-gray-400'}`}
                  strokeWidth={2}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-[13px] text-gray-800 line-clamp-1 flex-1">{pr.title}</p>
                    {pr.draft && (
                      <span className="text-[10px] font-semibold text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded border border-gray-200 flex-shrink-0">Draft</span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 mt-1 flex-wrap">
                    <span className="font-mono text-[11px] text-gray-400">#{pr.number}</span>
                    <StatusBadge status={pr.state} />
                    <span className="text-[11px] text-gray-400">{formatTimeAgo(pr.timestamp)}</span>
                    <div className="ml-auto flex gap-1">
                      {pr.labels.slice(0, 2).map(label => (
                        <span key={label} className="text-[10px] text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">{label}</span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="pt-2 border-t border-gray-100 flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-1.5">
            <Shield className="w-3.5 h-3.5 text-gray-400" />
            <span className="text-[12px] text-gray-500">
              {health.vulnerabilities === 0 ? 'No vulnerabilities' : `${health.vulnerabilities} vulnerabilities`}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-gray-400" />
            <span className="text-[12px] text-gray-500">Deployed {formatTimeAgo(health.lastDeploy)}</span>
          </div>
          <span className="ml-auto text-[12px] text-gray-400">{health.openIssues} open issues</span>
        </div>
      </div>
    </div>
  )
}
