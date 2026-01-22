import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import ErrorIcon from '@mui/icons-material/Error'
import ExpandLessIcon from '@mui/icons-material/ExpandLess'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import DeleteIcon from '@mui/icons-material/Delete'
import FileDownloadIcon from '@mui/icons-material/FileDownload'
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty'
import RefreshIcon from '@mui/icons-material/Refresh'
import SyncIcon from '@mui/icons-material/Sync'
import {
  Alert,
  Box,
  Button,
  Chip,
  Collapse,
  IconButton,
  LinearProgress,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from '@mui/material'
import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from 'react'

type KnownJobStatus = 'pending' | 'processing' | 'completed' | 'failed'
type JobStatus = KnownJobStatus | string

export type Job = {
  id: string
  filename: string
  status: JobStatus
  totalRows?: number | null
  processedRows?: number | null
  successCount?: number | null
  failedCount?: number | null
  errors?: string[] | null
  createdAt?: string | null
  completedAt?: string | null
}

type JobsResponse = {
  jobs: Job[]
  total: number
}

type JobWsEvent =
  | {
      type: 'snapshot'
      jobId: string
      filename?: string
      status?: string
      totalRows?: number | null
      processedRows?: number | null
      successCount?: number | null
      failedCount?: number | null
      createdAt?: string | null
      completedAt?: string | null
      ts?: string
    }
  | {
      type: 'progress'
      jobId: string
      rowNumber?: number
      rowOutcome?: 'success' | 'failed'
      error?: string | null
      totalRows?: number | null
      processedRows?: number | null
      successCount?: number | null
      failedCount?: number | null
      progress?: number
      ts?: string
    }
  | {
      type: 'status'
      jobId: string
      status: string
      message?: string
      totalRows?: number | null
      processedRows?: number | null
      successCount?: number | null
      failedCount?: number | null
      progress?: number
      ts?: string
    }
  | {
      type: 'error'
      jobId: string
      message: string
      ts?: string
    }

function normalizeStatus(status: string): KnownJobStatus | 'unknown' {
  const s = status.toLowerCase().trim()
  if (s === 'pending') return 'pending'
  if (s === 'processing') return 'processing'
  if (s === 'completed') return 'completed'
  if (s === 'failed') return 'failed'
  return 'unknown'
}

function statusBadge(status: string): {
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

function progressPercent(job: Job): number | null {
  const total = job.totalRows ?? null
  const processed = job.processedRows ?? null
  if (!total || total <= 0 || processed == null || processed < 0) return null
  return Math.max(0, Math.min(100, Math.round((processed / total) * 100)))
}

function progressUi(job: Job): {
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

function jobIsActive(job: Job): boolean {
  const s = normalizeStatus(job.status)
  return s !== 'completed' && s !== 'failed'
}

function toWsBaseUrl(originOrHttpUrl: string): string {
  const trimmed = originOrHttpUrl.trim()
  if (!trimmed) return ''
  if (trimmed.startsWith('ws://') || trimmed.startsWith('wss://')) return trimmed.replace(/\/+$/, '')
  if (trimmed.startsWith('http://')) return 'ws://' + trimmed.slice('http://'.length).replace(/\/+$/, '')
  if (trimmed.startsWith('https://')) return 'wss://' + trimmed.slice('https://'.length).replace(/\/+$/, '')
  return trimmed.replace(/\/+$/, '')
}

function getJobWsUrl(jobId: string): string {
  const envWsTarget = (import.meta.env.VITE_WS_TARGET as string | undefined) ?? ''
  const envApiTarget = (import.meta.env.VITE_API_TARGET as string | undefined) ?? ''
  const base =
    toWsBaseUrl(envWsTarget) ||
    toWsBaseUrl(envApiTarget) ||
    toWsBaseUrl(window.location.origin)

  return `${base}/ws/jobs/${encodeURIComponent(jobId)}`
}

export function JobsList(props: { refreshToken?: number }) {
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [open, setOpen] = useState<Record<string, boolean>>({})
  const jobsRef = useRef<Job[]>([])
  const socketsRef = useRef<Map<string, WebSocket>>(new Map())
  const reconnectTimersRef = useRef<Map<string, number>>(new Map())

  const toggleOpen = useCallback((id: string) => {
    setOpen((prev) => ({ ...prev, [id]: !prev[id] }))
  }, [])

  const fetchJobs = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/jobs', { method: 'GET' })
      if (!res.ok) {
        const text = await res.text().catch(() => '')
        throw new Error(text || `Failed to load jobs (${res.status})`)
      }
      const json = (await res.json()) as JobsResponse
      setJobs(json.jobs ?? [])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load jobs')
    } finally {
      setLoading(false)
    }
  }, [])

  const clearAll = useCallback(async () => {
    if (!window.confirm('Are you sure you want to delete all jobs and related data? This action cannot be undone.')) {
      return
    }
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/jobs/reset', { method: 'DELETE' })
      if (!res.ok) {
        const text = await res.text().catch(() => '')
        throw new Error(text || `Failed to clear all data (${res.status})`)
      }
      await fetchJobs()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to clear all data')
    } finally {
      setLoading(false)
    }
  }, [fetchJobs])

  useEffect(() => {
    void fetchJobs()
  }, [fetchJobs, props.refreshToken])

  useEffect(() => {
    jobsRef.current = jobs
  }, [jobs])

  const applyWsUpdate = useCallback(
    (jobId: string, patch: Partial<Job>) => {
      setJobs((prev) => {
        let changed = false
        const next = prev.map((j) => {
          if (j.id !== jobId) return j
          changed = true
          return { ...j, ...patch }
        })
        return changed ? next : prev
      })
    },
    [setJobs],
  )

  const closeSocket = useCallback((jobId: string) => {
    const t = reconnectTimersRef.current.get(jobId)
    if (t != null) {
      window.clearTimeout(t)
      reconnectTimersRef.current.delete(jobId)
    }
    const ws = socketsRef.current.get(jobId)
    if (ws) {
      try {
        ws.close()
      } catch {
        // ignore
      }
      socketsRef.current.delete(jobId)
    }
  }, [])

  const openSocket = useCallback(
    (job: Job) => {
      const jobId = job.id
      const existingTimer = reconnectTimersRef.current.get(jobId)
      if (existingTimer != null) {
        window.clearTimeout(existingTimer)
        reconnectTimersRef.current.delete(jobId)
      }
      if (socketsRef.current.has(jobId)) return

      const wsUrl = getJobWsUrl(jobId)
      let ws: WebSocket
      try {
        ws = new WebSocket(wsUrl)
      } catch {
        return
      }

      socketsRef.current.set(jobId, ws)

      ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(String(evt.data)) as JobWsEvent
          if (!msg || typeof msg !== 'object' || (msg as any).jobId !== jobId) return

          if (msg.type === 'snapshot') {
            applyWsUpdate(jobId, {
              filename: msg.filename ?? job.filename,
              status: msg.status ?? job.status,
              totalRows: msg.totalRows ?? null,
              processedRows: msg.processedRows ?? null,
              successCount: msg.successCount ?? null,
              failedCount: msg.failedCount ?? null,
              createdAt: msg.createdAt ?? job.createdAt ?? null,
              completedAt: msg.completedAt ?? job.completedAt ?? null,
            })
            return
          }

          if (msg.type === 'progress') {
            applyWsUpdate(jobId, {
              totalRows: msg.totalRows ?? null,
              processedRows: msg.processedRows ?? null,
              successCount: msg.successCount ?? null,
              failedCount: msg.failedCount ?? null,
            })
            return
          }

          if (msg.type === 'status') {
            applyWsUpdate(jobId, {
              status: msg.status,
              totalRows: msg.totalRows ?? null,
              processedRows: msg.processedRows ?? null,
              successCount: msg.successCount ?? null,
              failedCount: msg.failedCount ?? null,
            })
            const s = normalizeStatus(msg.status)
            if (s === 'completed' || s === 'failed') {
              // Pull final data (incl. full error list) once done.
              // Add a small delay to ensure backend has finished committing all errors
              setTimeout(() => {
                void fetchJobs()
              }, 500)
              closeSocket(jobId)
            }
            return
          }
        } catch {
        }
      }

      ws.onclose = () => {
        socketsRef.current.delete(jobId)

        if (reconnectTimersRef.current.has(jobId)) return
        const current = jobsRef.current.find((x) => x.id === jobId)
        if (!current || !jobIsActive(current)) return
        const t = window.setTimeout(() => {
          openSocket(current)
        }, 750)
        reconnectTimersRef.current.set(jobId, t)
      }
    },
    [applyWsUpdate, closeSocket, fetchJobs],
  )

  useEffect(() => {
    const activeIds = new Set(jobs.filter(jobIsActive).map((j) => j.id))

    for (const [jobId] of socketsRef.current.entries()) {
      if (!activeIds.has(jobId)) closeSocket(jobId)
    }


    for (const j of jobs) {
      if (!jobIsActive(j)) continue
      openSocket(j)
    }
  }, [jobs, closeSocket, openSocket])

  useEffect(() => {
    return () => {
      for (const [jobId] of socketsRef.current.entries()) closeSocket(jobId)
    }
  }, [closeSocket])

  const rows = useMemo(() => jobs, [jobs])

  return (
    <Paper elevation={2} sx={{ p: 2 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
        <Box>
          <Typography variant="h6" fontWeight={700}>
            Jobs
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Track filename, status, progress, counts, and errors.
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} alignItems="center">
          <Tooltip title="Clear all jobs">
            <span>
              <IconButton onClick={clearAll} disabled={loading || jobs.length === 0} aria-label="Clear all jobs" color="error">
                <DeleteIcon />
              </IconButton>
            </span>
          </Tooltip>
          <Tooltip title="Refresh">
            <span>
              <IconButton onClick={fetchJobs} disabled={loading} aria-label="Refresh jobs">
                <RefreshIcon />
              </IconButton>
            </span>
          </Tooltip>
        </Stack>
      </Stack>

      {loading ? <LinearProgress sx={{ mb: 2 }} /> : null}
      {error ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      ) : null}

      <TableContainer component={Paper} variant="outlined">
        <Table size="small" aria-label="jobs table">
          <TableHead>
            <TableRow>
              <TableCell width={40} />
              <TableCell>Filename</TableCell>
              <TableCell>Status</TableCell>
              <TableCell width="35%">Progress</TableCell>
              <TableCell>Counts</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6}>
                  <Typography variant="body2" color="text.secondary">
                    No jobs yet.
                  </Typography>
                </TableCell>
              </TableRow>
            ) : null}

            {rows.map((job) => {
              const p = progressUi(job)
              const isOpen = Boolean(open[job.id])
              const errors = job.errors ?? []
              const hasErrors = errors.length > 0
              const status = normalizeStatus(job.status)
              const isDone = status === 'completed' || status === 'failed'
              const badge = statusBadge(job.status)
              const idShort = job.id.length > 8 ? job.id.slice(0, 8) : job.id

              return (
                <Fragment key={job.id}>
                  <TableRow hover>
                    <TableCell>
                      <IconButton
                        size="small"
                        onClick={() => toggleOpen(job.id)}
                        aria-label={isOpen ? 'Collapse row' : 'Expand row'}
                      >
                        {isOpen ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                      </IconButton>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" fontWeight={600}>
                        {job.filename}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Job #{idShort}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        label={badge.label}
                        color={badge.color}
                        icon={badge.icon}
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>
                      <Stack spacing={0.5}>
                        <LinearProgress
                          variant={p.variant}
                          value={p.value}
                        />
                        <Typography variant="caption" color="text.secondary">
                          {p.label}
                        </Typography>
                      </Stack>
                    </TableCell>
                    <TableCell>
                      {isDone ? (
                        <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
                          <Chip size="small" color="success" label={`Success: ${job.successCount ?? 0}`} />
                          <Chip size="small" color="error" label={`Failed: ${job.failedCount ?? 0}`} />
                        </Stack>
                      ) : (
                        <Typography variant="body2" color="text.secondary">
                          —
                        </Typography>
                      )}
                    </TableCell>
                   
                  </TableRow>
                  <TableRow>
                    <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={6}>
                      <Collapse in={isOpen} timeout="auto" unmountOnExit>
                        <Box sx={{ py: 2, px: 2 }}>
                          <Stack spacing={1}>
                            <Typography variant="subtitle2" fontWeight={700}>
                              Details
                            </Typography>
                            <Stack direction="row" spacing={1} alignItems="center" useFlexGap flexWrap="wrap">
                              <Button
                                size="small"
                                variant="outlined"
                                startIcon={<FileDownloadIcon />}
                                component="a"
                                href={`/api/jobs/${encodeURIComponent(job.id)}/error-report`}
                                download={`job_${job.id}_error_report.csv`}
                                disabled={(job.failedCount ?? 0) <= 0}
                              >
                                Error report (CSV)
                              </Button>
                              <Typography variant="caption" color="text.secondary">
                                Failed rows: {job.failedCount ?? 0}
                              </Typography>
                            </Stack>
                            <Typography variant="body2" color="text.secondary">
                              Rows: {job.processedRows ?? 0}/{job.totalRows ?? 0}
                            </Typography>
                            {hasErrors ? (
                              <Box>
                                <Typography variant="subtitle2" sx={{ mb: 0.5 }}>
                                  Errors
                                </Typography>
                                <Stack spacing={0.5}>
                                  {errors.map((msg, idx) => (
                                    <Alert key={idx} severity="error" variant="outlined">
                                      {msg}
                                    </Alert>
                                  ))}
                                </Stack>
                              </Box>
                            ) : (
                              <Typography variant="body2" color="text.secondary">
                                No errors.
                              </Typography>
                            )}
                          </Stack>
                        </Box>
                      </Collapse>
                    </TableCell>
                  </TableRow>
                </Fragment>
              )
            })}
          </TableBody>
        </Table>
      </TableContainer>
    </Paper>
  )
}

