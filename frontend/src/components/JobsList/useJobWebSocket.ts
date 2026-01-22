import { useCallback, useEffect, useRef } from 'react'
import type { Job, JobWsEvent } from './types'
import { getJobWsUrl, jobIsActive, normalizeStatus } from './utils'

export function useJobWebSocket(
  jobs: Job[],
  onJobUpdate: (jobId: string, patch: Partial<Job>) => void,
  onJobComplete: () => void
) {
  const jobsRef = useRef<Job[]>([])
  const socketsRef = useRef<Map<string, WebSocket>>(new Map())
  const reconnectTimersRef = useRef<Map<string, number>>(new Map())

  useEffect(() => {
    jobsRef.current = jobs
  }, [jobs])

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
            onJobUpdate(jobId, {
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
            onJobUpdate(jobId, {
              totalRows: msg.totalRows ?? null,
              processedRows: msg.processedRows ?? null,
              successCount: msg.successCount ?? null,
              failedCount: msg.failedCount ?? null,
            })
            return
          }

          if (msg.type === 'status') {
            onJobUpdate(jobId, {
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
                onJobComplete()
              }, 500)
              closeSocket(jobId)
            }
            return
          }
        } catch {
          // ignore parse errors
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
    [onJobUpdate, onJobComplete, closeSocket],
  )

  // Manage socket connections based on active jobs
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

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      for (const [jobId] of socketsRef.current.entries()) closeSocket(jobId)
    }
  }, [closeSocket])
}
