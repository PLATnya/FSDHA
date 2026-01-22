import FileDownloadIcon from '@mui/icons-material/FileDownload'
import { Alert, Box, Button, Stack, Typography } from '@mui/material'
import type { Job } from './types'

interface JobDetailsProps {
  job: Job
}

export function JobDetails({ job }: JobDetailsProps) {
  const errors = job.errors ?? []
  const hasErrors = errors.length > 0

  return (
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
  )
}
