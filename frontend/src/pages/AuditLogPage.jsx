import {
  Box, Chip, MenuItem, Paper, Stack, Table, TableBody, TableCell, TableContainer, TableHead,
  TablePagination, TableRow, TextField, Typography,
} from '@mui/material';
import { useState } from 'react';
import { api } from '../api/client.js';
import ErrorAlert from '../components/ErrorAlert.jsx';
import Loading from '../components/Loading.jsx';
import PageHeader from '../components/PageHeader.jsx';
import useIsMobile from '../hooks/useIsMobile.js';
import useLoader from '../hooks/useLoader.js';
import { formatDateTime, fullName } from '../utils/format.js';

const ACTIONS = ['create', 'update', 'archive', 'restore', 'assign_role', 'assign_team', 'complete', 'abandon'];
const TYPES = ['user', 'project', 'milestone', 'hour_assignment'];

function show(value) {
  if (value === null || value === undefined || value === '') return '∅';
  if (Array.isArray(value)) return value.join(', ');
  return String(value);
}

// [AUDIT LOG PAGE HERE]
// How: Admins page through every recorded change, newest first, filtered by
//      person, action, item type, and date range. Each row lists exactly
//      which fields changed, from what to what. There are no edit or delete
//      controls, because entries can never be changed.
// Why: The requirements make the audit log admin-only and permanent; this
//      is how admins answer "who changed this, and when?".
/** Admin-only, read-only history of every change. */
export default function AuditLogPage() {
  const isMobile = useIsMobile();
  const [filters, setFilters] = useState({ actor_id: '', action: '', entity_type: '', from: '', to: '' });
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);

  const users = useLoader(() => api('/users', { query: { include_archived: 'true' } }).then((d) => d.users), []);
  const { data, loading, error, reload } = useLoader(
    () => api('/audit-log', { query: { ...filters, limit: rowsPerPage, offset: page * rowsPerPage } }),
    [JSON.stringify(filters), page, rowsPerPage],
  );
  const names = Object.fromEntries((users.data || []).map((u) => [u.id, fullName(u)]));
  const setFilter = (field) => (event) => {
    setFilters({ ...filters, [field]: event.target.value });
    setPage(0);
  };

  return (
    <>
      <PageHeader title="Audit log" subtitle="Every change, who made it, and when. Entries can't be edited or deleted." />
      <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', lg: 'repeat(5, 1fr)' }, mb: 2 }}>
        <TextField select label="Person" value={filters.actor_id} onChange={setFilter('actor_id')}>
          <MenuItem value="">Anyone</MenuItem>
          {(users.data || []).map((u) => <MenuItem key={u.id} value={u.id}>{fullName(u)}</MenuItem>)}
        </TextField>
        <TextField select label="Action" value={filters.action} onChange={setFilter('action')}>
          <MenuItem value="">Any action</MenuItem>
          {ACTIONS.map((a) => <MenuItem key={a} value={a}>{a.replace('_', ' ')}</MenuItem>)}
        </TextField>
        <TextField select label="Item type" value={filters.entity_type} onChange={setFilter('entity_type')}>
          <MenuItem value="">Any type</MenuItem>
          {TYPES.map((t) => <MenuItem key={t} value={t}>{t.replace('_', ' ')}</MenuItem>)}
        </TextField>
        <TextField label="From" type="date" value={filters.from} onChange={setFilter('from')} slotProps={{ inputLabel: { shrink: true } }} />
        <TextField label="To" type="date" value={filters.to} onChange={setFilter('to')} slotProps={{ inputLabel: { shrink: true } }} />
      </Box>

      <ErrorAlert error={error} onRetry={reload} />
      {loading && !data && <Loading label="Loading audit log" />}
      {data && (
        <Paper variant="outlined">
          <TableContainer>
            <Table size="small" aria-label="Audit log">
              <TableHead>
                <TableRow>
                  <TableCell>When</TableCell>
                  <TableCell>Who</TableCell>
                  <TableCell>Action</TableCell>
                  {!isMobile && <TableCell>Item</TableCell>}
                  <TableCell>Changes</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.entries.length === 0 && (
                  <TableRow><TableCell colSpan={5}><Typography color="text.secondary">No entries match.</Typography></TableCell></TableRow>
                )}
                {data.entries.map((entry) => (
                  <TableRow key={entry.id} sx={{ verticalAlign: 'top' }}>
                    <TableCell sx={{ whiteSpace: 'nowrap' }}>{formatDateTime(entry.created_at)}</TableCell>
                    <TableCell>{entry.actor_id ? names[entry.actor_id] || 'Unknown' : 'System'}</TableCell>
                    <TableCell><Chip size="small" label={entry.action.replace('_', ' ')} /></TableCell>
                    {!isMobile && (
                      <TableCell>
                        {entry.entity_type.replace('_', ' ')}
                        {entry.entity_type === 'user' && names[entry.entity_id] && <><br /><Typography variant="caption">{names[entry.entity_id]}</Typography></>}
                      </TableCell>
                    )}
                    <TableCell>
                      <Stack spacing={0.25}>
                        {Object.entries(entry.changes).slice(0, 8).map(([field, change]) => (
                          <Typography key={field} variant="body2" sx={{ wordBreak: 'break-word' }}>
                            <strong>{field}</strong>: {entry.action === 'create' ? show(change.after) : `${show(change.before)} → ${show(change.after)}`}
                          </Typography>
                        ))}
                        {Object.keys(entry.changes).length > 8 && (
                          <Typography variant="caption" color="text.secondary">+{Object.keys(entry.changes).length - 8} more fields</Typography>
                        )}
                      </Stack>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
          <TablePagination
            component="div"
            count={data.total}
            page={page}
            onPageChange={(_, next) => setPage(next)}
            rowsPerPage={rowsPerPage}
            onRowsPerPageChange={(event) => { setRowsPerPage(Number(event.target.value)); setPage(0); }}
            rowsPerPageOptions={[25, 50, 100]}
          />
        </Paper>
      )}
    </>
  );
}
