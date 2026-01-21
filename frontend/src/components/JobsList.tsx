import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import ErrorIcon from '@mui/icons-material/Error'
import ExpandLessIcon from '@mui/icons-material/ExpandLess'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty'
import RefreshIcon from '@mui/icons-material/Refresh'
import SyncIcon from '@mui/icons-material/Sync'
import {
  Alert,
  Box,
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
import { Fragment, useCallback, useEffect, useMemo, useState } from 'react'

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

export function JobsList(props: { refreshToken?: number }) {
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [open, setOpen] = useState<Record<string, boolean>>({})

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

  useEffect(() => {
    void fetchJobs()
  }, [fetchJobs, props.refreshToken])

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
        <Tooltip title="Refresh">
          <span>
            <IconButton onClick={fetchJobs} disabled={loading} aria-label="Refresh jobs">
              <RefreshIcon />
            </IconButton>
          </span>
        </Tooltip>
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
              const firstError = hasErrors ? errors[0] : null

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

