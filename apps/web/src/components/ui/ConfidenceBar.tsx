import { cn } from '@/lib/utils'

interface ConfidenceBarProps {
  score: number // 0 – 1
  showLabel?: boolean
  className?: string
}

export function ConfidenceBar({ score, showLabel = true, className }: ConfidenceBarProps) {
  const pct = Math.round(score * 100)

  const color =
    pct >= 85 ? 'bg-emerald-500' : pct >= 65 ? 'bg-amber-400' : 'bg-rose-400'

  const label = pct >= 85 ? 'High' : pct >= 65 ? 'Medium' : 'Low'
  const textColor = pct >= 85 ? 'text-emerald-700' : pct >= 65 ? 'text-amber-700' : 'text-rose-600'

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all', color)}
          style={{ width: `${pct}%` }}
        />
      </div>
      {showLabel && (
        <span className={cn('text-xs font-medium tabular-nums', textColor)}>
          {label} ({pct}%)
        </span>
      )}
    </div>
  )
}

interface ConfidenceBadgeProps {
  score: number
}

export function ConfidenceBadge({ score }: ConfidenceBadgeProps) {
  const pct = Math.round(score * 100)
  const className =
    pct >= 85
      ? 'bg-emerald-50 text-emerald-700'
      : pct >= 65
      ? 'bg-amber-50 text-amber-700'
      : 'bg-rose-50 text-rose-600'

  return (
    <span className={cn('inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold tabular-nums', className)}>
      {pct}%
    </span>
  )
}
