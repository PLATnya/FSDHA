import ExpandLessIcon from '@mui/icons-material/ExpandLess'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import {
  Chip,
  Collapse,
  IconButton,
  LinearProgress,
  Stack,
  TableCell,
  TableRow,
  Typography,
} from '@mui/material'
import { Fragment } from 'react'
import type { Job } from './types'
import { normalizeStatus, progressUi, statusBadge } from './utils'
import { JobDetails } from './JobDetails'

interface JobRowProps {
  job: Job
  isOpen: boolean
  onToggle: () => void
}

export function JobRow({ job, isOpen, onToggle }: JobRowProps) {
  const p = progressUi(job)
  const status = normalizeStatus(job.status)
  const isDone = status === 'completed' || status === 'failed'
  const badge = statusBadge(job.status)
  const idShort = job.id.length > 8 ? job.id.slice(0, 8) : job.id

  return (
    <Fragment>
      <TableRow hover>
        <TableCell>
          <IconButton
            size="small"
            onClick={onToggle}
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
            <LinearProgress variant={p.variant} value={p.value} />
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
            <JobDetails job={job} />
          </Collapse>
        </TableCell>
      </TableRow>
    </Fragment>
  )
}
