import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import ErrorIcon from '@mui/icons-material/Error'
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty'
import SyncIcon from '@mui/icons-material/Sync'
import type { Job, KnownJobStatus } from './types'

export function normalizeStatus(status: string): KnownJobStatus | 'unknown' {
  const s = status.toLowerCase().trim()
  if (s === 'pending') return 'pending'
  if (s === 'processing') return 'processing'
  if (s === 'completed') return 'completed'
  if (s === 'failed') return 'failed'
  return 'unknown'
}

export function statusBadge(status: string): {
  label: string
  color: 'default' | 'warning' | 'info' | 'success' | 'error'
  icon?: React.ReactElement
} {
  switch (normalizeStatus(status)) {
    case 'pending':
      return { label: 'pending', color: 'warning', icon: <HourglassEmptyIcon fontSize="small" /> }
    case 'processing':
      return { label: 'processing', color: 'info', icon: <SyncIcon fontSize="small" /> }
    case 'completed':
      return { label: 'completed', color: 'success', icon: <CheckCircleIcon fontSize="small" /> }
    case 'failed':
      return { label: 'failed', color: 'error', icon: <ErrorIcon fontSize="small" /> }
    default:
      return { label: status || 'unknown', color: 'default' }
  }
}

export function progressPercent(job: Job): number | null {
  const total = job.totalRows ?? null
  const processed = job.processedRows ?? null
  if (!total || total <= 0 || processed == null || processed < 0) return null
  return Math.max(0, Math.min(100, Math.round((processed / total) * 100)))
}

export function progressUi(job: Job): {
  variant: 'determinate' | 'indeterminate'
  value: number
  label: string
} {
  const status = normalizeStatus(job.status)
  const pct = progressPercent(job)
  const total = job.totalRows ?? null
  const processed = job.processedRows ?? null

  if (pct != null) {
    return {
      variant: 'determinate',
      value: pct,
      label: `${pct}% (${processed ?? 0}/${total ?? 0})`,
    }
  }

  if (status === 'completed') {
    return { variant: 'determinate', value: 100, label: '100%' }
  }

  if (status === 'pending') {
    return { variant: 'determinate', value: 0, label: '0%' }
  }

  if (processed != null && total != null) {
    return { variant: 'indeterminate', value: 0, label: `${processed}/${total}` }
  }

  return { variant: 'indeterminate', value: 0, label: '—' }
}

export function jobIsActive(job: Job): boolean {
  const s = normalizeStatus(job.status)
  return s !== 'completed' && s !== 'failed'
}

export function toWsBaseUrl(originOrHttpUrl: string): string {
  const trimmed = originOrHttpUrl.trim()
  if (!trimmed) return ''
  if (trimmed.startsWith('ws://') || trimmed.startsWith('wss://')) return trimmed.replace(/\/+$/, '')
  if (trimmed.startsWith('http://')) return 'ws://' + trimmed.slice('http://'.length).replace(/\/+$/, '')
  if (trimmed.startsWith('https://')) return 'wss://' + trimmed.slice('https://'.length).replace(/\/+$/, '')
  return trimmed.replace(/\/+$/, '')
}

export function getJobWsUrl(jobId: string): string {
  const envWsTarget = (import.meta.env.VITE_WS_TARGET as string | undefined) ?? ''
  const envApiTarget = (import.meta.env.VITE_API_TARGET as string | undefined) ?? ''
  const base =
    toWsBaseUrl(envWsTarget) ||
    toWsBaseUrl(envApiTarget) ||
    toWsBaseUrl(window.location.origin)

  return `${base}/ws/jobs/${encodeURIComponent(jobId)}`
}
