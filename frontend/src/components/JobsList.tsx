import DeleteIcon from '@mui/icons-material/Delete'
import RefreshIcon from '@mui/icons-material/Refresh'
import {
  Alert,
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
import { useCallback, useEffect, useMemo, useState } from 'react'
import { JobRow } from './JobsList/JobRow'
import type { Job, JobsResponse } from './JobsList/types'
import { useJobWebSocket } from './JobsList/useJobWebSocket'

export function JobsList(props: { refreshToken?: number; newJobId?: string | null }) {
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

  const fetchAndAddJob = useCallback(async (jobId: string) => {
    try {
      const res = await fetch(`/api/jobs/${encodeURIComponent(jobId)}`, { method: 'GET' })
      if (!res.ok) {
        const text = await res.text().catch(() => '')
        throw new Error(text || `Failed to load job (${res.status})`)
      }
      const job = (await res.json()) as Job
      setJobs((prev) => {
        // Check if job already exists in the list
        const exists = prev.some((j) => j.id === job.id)
        if (exists) {
          // Update existing job
          return prev.map((j) => (j.id === job.id ? job : j))
        }
        // Add new job at the beginning of the list
        return [job, ...prev]
      })
    } catch (e) {
      console.error('Failed to fetch job:', e)
      // Silently fail - don't show error for individual job fetch
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
    [],
  )

  useJobWebSocket(jobs, applyWsUpdate, fetchJobs)

  useEffect(() => {
    void fetchJobs()
  }, [fetchJobs, props.refreshToken])

  useEffect(() => {
    if (props.newJobId) {
      void fetchAndAddJob(props.newJobId)
    }
  }, [props.newJobId, fetchAndAddJob])

  const rows = useMemo(() => jobs, [jobs])

  return (
    <Paper elevation={2} sx={{ p: 2 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
        <Stack>
          <Typography variant="h6" fontWeight={700}>
            Jobs
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Track filename, status, progress, counts, and errors.
          </Typography>
        </Stack>
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

            {rows.map((job) => (
              <JobRow
                key={job.id}
                job={job}
                isOpen={Boolean(open[job.id])}
                onToggle={() => toggleOpen(job.id)}
              />
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Paper>
  )
}
