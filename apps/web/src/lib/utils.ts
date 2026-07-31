import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

export function formatRelativeTime(iso: string): string {
  const now = Date.now()
  const then = new Date(iso).getTime()
  const diff = now - then
  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (days > 7) return formatDate(iso)
  if (days > 1) return `${days}d ago`
  if (days === 1) return 'Yesterday'
  if (hours > 1) return `${hours}h ago`
  if (hours === 1) return '1h ago'
  if (minutes > 1) return `${minutes}m ago`
  return 'Just now'
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function getInitials(name: string): string {
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
}

export function confidenceToLabel(score: number): { label: string; color: string } {
  if (score >= 0.85) return { label: 'High', color: 'text-emerald-600' }
  if (score >= 0.65) return { label: 'Medium', color: 'text-amber-600' }
  return { label: 'Low', color: 'text-rose-500' }
}
