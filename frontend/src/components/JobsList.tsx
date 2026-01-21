import ExpandLessIcon from '@mui/icons-material/ExpandLess'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import RefreshIcon from '@mui/icons-material/Refresh'
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

type JobStatus = string

export type Job = {
  id: number
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

function statusChipColor(status: string): 'default' | 'warning' | 'info' | 'success' | 'error' {
  const s = status.toLowerCase()
  if (s.includes('fail') || s.includes('error')) return 'error'
  if (s.includes('complete') || s.includes('done') || s.includes('success')) return 'success'
  if (s.includes('process') || s.includes('running')) return 'info'
  if (s.includes('queue') || s.includes('pending')) return 'warning'
  return 'default'
}

function progressPercent(job: Job): number | null {
  const total = job.totalRows ?? null
  const processed = job.processedRows ?? null
  if (!total || total <= 0 || processed == null || processed < 0) return null
  return Math.max(0, Math.min(100, Math.round((processed / total) * 100)))
}

export function JobsList(props: { refreshToken?: number }) {
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [open, setOpen] = useState<Record<number, boolean>>({})

  const toggleOpen = useCallback((id: number) => {
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
              <TableCell>Errors</TableCell>
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
              const pct = progressPercent(job)
              const isOpen = Boolean(open[job.id])
              const errors = job.errors ?? []
              const hasErrors = errors.length > 0
              const isCompleted = job.status?.toLowerCase().includes('complete')

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
                        Job #{job.id}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip size="small" label={job.status} color={statusChipColor(job.status)} />
                    </TableCell>
                    <TableCell>
                      <Stack spacing={0.5}>
                        <LinearProgress
                          variant={pct == null ? 'indeterminate' : 'determinate'}
                          value={pct ?? 0}
                        />
                        <Typography variant="caption" color="text.secondary">
                          {pct == null
                            ? job.processedRows != null && job.totalRows != null
                              ? `${job.processedRows}/${job.totalRows}`
                              : '—'
                            : `${pct}% (${job.processedRows ?? 0}/${job.totalRows ?? 0})`}
                        </Typography>
                      </Stack>
                    </TableCell>
                    <TableCell>
                      {isCompleted ? (
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
                    <TableCell>
                      {hasErrors ? (
                        <Chip size="small" color="error" variant="outlined" label={`${errors.length} error(s)`} />
                      ) : (
                        <Typography variant="body2" color="text.secondary">
                          None
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

