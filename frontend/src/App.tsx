import CloudUploadIcon from '@mui/icons-material/CloudUpload'
import UploadFileIcon from '@mui/icons-material/UploadFile'
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Container,
  Paper,
  Stack,
  Typography,
} from '@mui/material'
import { useMemo, useState } from 'react'
import { JobsList } from './components/JobsList'

function App() {
  const [file, setFile] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<{ id: string; filename: string; status: string } | null>(null)
  const [jobsRefreshToken, setJobsRefreshToken] = useState(0)

  const fileLabel = useMemo(() => {
    if (!file) return 'No file selected'
    return `${file.name} (${Math.ceil(file.size / 1024)} KB)`
  }, [file])

  async function onUpload() {
    if (!file || isUploading) return
    setIsUploading(true)
    setError(null)
    setResult(null)

    try {
      const form = new FormData()
      form.append('file', file)

      const res = await fetch('/api/jobs/upload', {
        method: 'POST',
        body: form,
      })

      if (!res.ok) {
        const text = await res.text().catch(() => '')
        throw new Error(text || `Upload failed (${res.status})`)
      }

      const json = (await res.json()) as { id: string; filename: string; status: string }
      setResult(json)
      setJobsRefreshToken((x) => x + 1)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed')
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <Box sx={{ minHeight: '100%', py: 6 }}>
      <Container maxWidth={false} sx={{ maxWidth: 1350 }}>
        <Stack spacing={3}>
          <Paper elevation={2} sx={{ p: 3 }}>
            <Stack spacing={2.5}>
              <Box>
                <Typography variant="h5" fontWeight={700}>
                  CSV Upload
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Select a CSV file and upload it for processing.
                </Typography>
              </Box>

              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems={{ sm: 'center' }}>
                <Chip
                  icon={<UploadFileIcon />}
                  label={fileLabel}
                  color={file ? 'success' : 'default'}
                  variant={file ? 'filled' : 'outlined'}
                  sx={{ flex: 1, justifyContent: 'flex-start' }}
                />

                <Button
                  component="label"
                  variant="outlined"
                  disabled={isUploading}
                  sx={{ whiteSpace: 'nowrap' }}
                >
                  Choose CSV
                  <input
                    type="file"
                    accept=".csv,text/csv"
                    hidden
                    onChange={(e) => {
                      const next = e.target.files?.[0] ?? null
                      setFile(next)
                      setError(null)
                      setResult(null)
                    }}
                  />
                </Button>
              </Stack>

              <Button
                variant="contained"
                startIcon={isUploading ? undefined : <CloudUploadIcon />}
                onClick={onUpload}
                disabled={!file || isUploading}
              >
                {isUploading ? (
                  <>
                    <CircularProgress size={18} sx={{ mr: 1 }} color="inherit" />
                    Uploading…
                  </>
                ) : (
                  'Upload'
                )}
              </Button>

              {error ? <Alert severity="error">{error}</Alert> : null}
              {result ? (
                <Alert severity="success">
                  Uploaded: job #{result.id} ({result.filename}) — {result.status}
                </Alert>
              ) : null}
            </Stack>
          </Paper>

          <JobsList refreshToken={jobsRefreshToken} />
        </Stack>
      </Container>
    </Box>
  )
}

export default App
