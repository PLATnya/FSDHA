export type KnownJobStatus = 'pending' | 'processing' | 'completed' | 'failed'
export type JobStatus = KnownJobStatus | string

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

export type JobsResponse = {
  jobs: Job[]
  total: number
}

export type JobWsEvent =
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
