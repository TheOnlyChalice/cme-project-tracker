import {
  Box, Chip, Link, MenuItem, Paper, Stack, Table, TableBody, TableCell, TableContainer, TableHead,
  TablePagination, TableRow, TextField, Typography,
} from '@mui/material';
import PropTypes from 'prop-types';
import { useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { api } from '../api/client.js';
import useIsMobile from '../hooks/useIsMobile.js';
import useLoader from '../hooks/useLoader.js';
import { useT } from '../i18n/LanguageContext.js';
import { formatDateTime, fullName } from '../utils/format.js';
import ErrorAlert from './ErrorAlert.jsx';
import Loading from './Loading.jsx';

const ACTIONS = {
  create: 'Created', update: 'Updated', archive: 'Archived', restore: 'Restored',
  assign_role: 'Role changed', assign_team: 'Manager changed', complete: 'Completed', abandon: 'Abandoned',
};
export const ITEM_TYPES = { user: 'Person', project: 'Project', milestone: 'Milestone', hour_assignment: 'Hours' };

function show(value) {
  if (value === null || value === undefined || value === '') return '∅';
  if (Array.isArray(value)) return value.join(', ');
  return String(value);
}

// [AUDIT LOG TABLE HERE]
// How: One shared, read-only table used by both audit logs: the general one
//      (people and accounts) and each project's own. It pages through
//      entries newest first, with filters for person, action, item type (when
//      the log has more than one type), and a date range, and lists exactly
//      which fields changed, from what to what.
// Why: Both logs look and behave the same, so admins only learn it once.
//      There are no edit or delete controls, because entries can never change.
/** A filterable, paged, read-only list of audit entries from one endpoint. */
export default function AuditLogTable({ path, itemTypes, itemName = () => '' }) {
  const t = useT();
  const isMobile = useIsMobile();
  const [filters, setFilters] = useState({ actor_id: '', action: '', entity_type: '', from: '', to: '' });
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);

  const users = useLoader(() => api('/users', { query: { include_archived: 'true' } }).then((d) => d.users), []);
  const { data, loading, error, reload } = useLoader(
    () => api(path, { query: { ...filters, limit: rowsPerPage, offset: page * rowsPerPage } }),
    [path, JSON.stringify(filters), page, rowsPerPage],
  );
  const names = Object.fromEntries((users.data || []).map((u) => [u.id, fullName(u)]));
  const setFilter = (field) => (event) => {
    setFilters({ ...filters, [field]: event.target.value });
    setPage(0);
  };
  const columns = isMobile ? 4 : 5;

  return (
    <Stack spacing={2}>
      <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', lg: `repeat(${itemTypes.length > 1 ? 5 : 4}, 1fr)` } }}>
        <TextField select label={t('Person')} value={filters.actor_id} onChange={setFilter('actor_id')}>
          <MenuItem value="">{t('Anyone')}</MenuItem>
          {(users.data || []).map((u) => <MenuItem key={u.id} value={u.id}>{fullName(u)}</MenuItem>)}
        </TextField>
        <TextField select label={t('Action')} value={filters.action} onChange={setFilter('action')}>
          <MenuItem value="">{t('Any action')}</MenuItem>
          {Object.entries(ACTIONS).map(([value, label]) => <MenuItem key={value} value={value}>{t(label)}</MenuItem>)}
        </TextField>
        {itemTypes.length > 1 && (
          <TextField select label={t('Item type')} value={filters.entity_type} onChange={setFilter('entity_type')}>
            <MenuItem value="">{t('Any type')}</MenuItem>
            {itemTypes.map((type) => <MenuItem key={type} value={type}>{t(ITEM_TYPES[type])}</MenuItem>)}
          </TextField>
        )}
        <TextField label={t('From')} type="date" value={filters.from} onChange={setFilter('from')} slotProps={{ inputLabel: { shrink: true } }} />
        <TextField label={t('To')} type="date" value={filters.to} onChange={setFilter('to')} slotProps={{ inputLabel: { shrink: true } }} />
      </Box>

      <ErrorAlert error={error} onRetry={reload} />
      {loading && !data && <Loading label="Loading audit log" />}
      {data && (
        <Paper variant="outlined">
          <TableContainer>
            <Table size="small" aria-label={t('Audit log')}>
              <TableHead>
                <TableRow>
                  <TableCell>{t('When')}</TableCell>
                  <TableCell>{t('Who')}</TableCell>
                  <TableCell>{t('Action')}</TableCell>
                  {!isMobile && <TableCell>{t('Item')}</TableCell>}
                  <TableCell>{t('Changes')}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.entries.length === 0 && (
                  <TableRow><TableCell colSpan={columns}><Typography color="text.secondary">{t('No entries match.')}</Typography></TableCell></TableRow>
                )}
                {data.entries.map((entry) => (
                  <TableRow key={entry.id} sx={{ verticalAlign: 'top' }}>
                    <TableCell sx={{ whiteSpace: 'nowrap' }}>{formatDateTime(entry.created_at)}</TableCell>
                    <TableCell>
                      {/* [AUDIT LINKS HERE]
                          How: The person who made a change, and a person who was
                               changed, link to their person page.
                          Why: Following up on an audit entry usually means looking
                               at that person next. */}
                      {entry.actor_id && names[entry.actor_id]
                        ? <Link component={RouterLink} to={`/people/${entry.actor_id}`} underline="hover" color="inherit">{names[entry.actor_id]}</Link>
                        : (entry.actor_id ? t('Unknown') : t('System'))}
                    </TableCell>
                    <TableCell><Chip size="small" label={t(ACTIONS[entry.action] || entry.action)} /></TableCell>
                    {!isMobile && (
                      <TableCell>
                        {t(ITEM_TYPES[entry.entity_type] || entry.entity_type)}
                        {itemName(entry, names) && (
                          <>
                            <br />
                            {entry.entity_type === 'user'
                              ? <Link component={RouterLink} to={`/people/${entry.entity_id}`} underline="hover" variant="caption">{itemName(entry, names)}</Link>
                              : <Typography variant="caption">{itemName(entry, names)}</Typography>}
                          </>
                        )}
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
                          <Typography variant="caption" color="text.secondary">{t('+{count} more fields', { count: Object.keys(entry.changes).length - 8 })}</Typography>
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
            labelRowsPerPage={t('Rows per page:')}
            labelDisplayedRows={({ from, to, count }) => t('{from}–{to} of {count}', { from, to, count })}
          />
        </Paper>
      )}
    </Stack>
  );
}

AuditLogTable.propTypes = {
  path: PropTypes.string.isRequired,
  itemTypes: PropTypes.arrayOf(PropTypes.string).isRequired,
  itemName: PropTypes.func,
};
