import AddIcon from '@mui/icons-material/Add';
import ArchiveIcon from '@mui/icons-material/Archive';
import EditIcon from '@mui/icons-material/Edit';
import SearchIcon from '@mui/icons-material/Search';
import UnarchiveIcon from '@mui/icons-material/Unarchive';
import {
  Avatar, Box, Button, FormControlLabel, IconButton, InputAdornment, MenuItem, Paper, Stack, Switch,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField, Tooltip, Typography,
} from '@mui/material';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client.js';
import { useAuth } from '../auth/AuthContext.js';
import ConfirmDialog from '../components/ConfirmDialog.jsx';
import ErrorAlert from '../components/ErrorAlert.jsx';
import UserDialog from '../components/forms/UserDialog.jsx';
import Loading from '../components/Loading.jsx';
import { useNotify } from '../components/NotifyContext.js';
import PageHeader from '../components/PageHeader.jsx';
import Paginator from '../components/Paginator.jsx';
import StatusChip from '../components/StatusChip.jsx';
import useDebouncedValue from '../hooks/useDebouncedValue.js';
import useIsMobile from '../hooks/useIsMobile.js';
import useLoader from '../hooks/useLoader.js';
import usePagination from '../hooks/usePagination.js';
import { useT } from '../i18n/LanguageContext.js';
import { formatMoney, fullName } from '../utils/format.js';
import { isAdmin } from '../utils/roles.js';

// [PEOPLE PAGE HERE]
// How: Managers see themselves and their team; admins see everyone and can
//      create, edit, archive, and restore people. Search and role filters
//      run on the backend after its visibility rules.
// Why: Matches the roles: only admins create users and assign roles, and
//      managers only see the people who report to them.
/** People directory; admins can also manage accounts. */
export default function PeoplePage() {
  const { user } = useAuth();
  const t = useT();
  const navigate = useNavigate();
  const admin = isAdmin(user);
  const isMobile = useIsMobile();
  const notify = useNotify();
  const [search, setSearch] = useState('');
  const [role, setRole] = useState('');
  const [archived, setArchived] = useState(false);
  const [dialog, setDialog] = useState(null);
  const query = useDebouncedValue(search);

  const { data, loading, error, reload } = useLoader(
    () => api('/users', { query: { search: query, role, include_archived: archived ? 'true' : '' } }).then((d) => d.users),
    [query, role, archived],
  );
  const everyone = useLoader(() => (admin ? api('/users').then((d) => d.users) : Promise.resolve([])), [admin]);
  const managers = (everyone.data || []).filter((u) => u.role !== 'employee');
  const names = Object.fromEntries((everyone.data || data || []).map((u) => [u.id, fullName(u)]));
  // [PEOPLE PAGING HERE]
  // How: The directory shows 25 people per page (10, 25, 50, or 100), after
  //      search and role filters are applied.
  // Why: Admins now see 80+ people; one long table was hard to scan.
  const pager = usePagination(data, 25);
  const close = () => setDialog(null);
  const refresh = () => {
    reload();
    everyone.reload();
  };

  return (
    <>
      <PageHeader
        title={t('People')}
        subtitle={admin ? t('Everyone in the company.') : t('You and the people who report to you.')}
        actions={admin && <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialog({ type: 'edit' })}>{t('New person')}</Button>}
      />
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 2 }} alignItems={{ sm: 'center' }}>
        <TextField label={t('Search by name, email, or username')} value={search} onChange={(e) => setSearch(e.target.value)}
          sx={{ maxWidth: { sm: 340 } }}
          slotProps={{ input: { startAdornment: <InputAdornment position="start"><SearchIcon /></InputAdornment> } }} />
        <TextField select label={t('Role')} value={role} onChange={(e) => setRole(e.target.value)} sx={{ maxWidth: { sm: 160 } }}>
          <MenuItem value="">{t('All roles')}</MenuItem>
          <MenuItem value="employee">{t('Employees')}</MenuItem>
          <MenuItem value="manager">{t('Managers')}</MenuItem>
          <MenuItem value="admin">{t('Admins')}</MenuItem>
        </TextField>
        {admin && <FormControlLabel control={<Switch checked={archived} onChange={(e) => setArchived(e.target.checked)} />} label={t('Include archived')} />}
      </Stack>

      <ErrorAlert error={error} onRetry={reload} />
      {loading && !data && <Loading label="Loading people" />}
      {data && data.length === 0 && <Typography color="text.secondary">{t('Nobody matches.')}</Typography>}
      {data && data.length > 0 && (
        <TableContainer component={Paper} variant="outlined">
          <Table size="small" aria-label={t('People')}>
            <TableHead>
              <TableRow>
                <TableCell>{t('Name')}</TableCell>
                {!isMobile && <TableCell>{t('Username')}</TableCell>}
                <TableCell>{t('Role')}</TableCell>
                {!isMobile && <TableCell>{t('Reports to')}</TableCell>}
                {!isMobile && admin && <TableCell align="right">{t('Salary')}</TableCell>}
                {admin && <TableCell align="right">{t('Actions')}</TableCell>}
              </TableRow>
            </TableHead>
            <TableBody>
              {pager.pageItems.map((person) => (
                <TableRow key={person.id} hover
                  sx={{ opacity: person.is_archived ? 0.6 : 1, cursor: 'pointer' }}
                  // [PERSON ROW LINK HERE]
                  // How: Clicking a row opens that person's page (unless text was
                  //      being selected, or a button in the row was clicked).
                  // Why: The directory is the natural way into someone's details.
                  onClick={(event) => {
                    if (event.target.closest('button') || window.getSelection()?.toString()) return;
                    navigate(`/people/${person.id}`);
                  }}>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                      <Avatar src={person.profile_picture_url || undefined} sx={{ width: 32, height: 32 }}>
                        {person.first_name[0]}{person.last_name[0]}
                      </Avatar>
                      <Box>
                        <Typography fontWeight={600}>{fullName(person)}{person.id === user.id && ` (${t('you')})`}</Typography>
                        <Typography variant="body2" color="text.secondary">{person.job_title || person.email}</Typography>
                      </Box>
                    </Box>
                  </TableCell>
                  {!isMobile && <TableCell><code>{person.username}</code></TableCell>}
                  <TableCell>
                    <Stack direction="row" spacing={0.5}>
                      <StatusChip value={person.role} />
                      {person.is_archived && <StatusChip archived />}
                      {person.locked_until && new Date(person.locked_until) > new Date() && (
                        <Tooltip title={t('Locked after too many wrong passwords. Set a new password to unlock.')}>
                          <span><StatusChip value="locked" /></span>
                        </Tooltip>
                      )}
                    </Stack>
                  </TableCell>
                  {!isMobile && <TableCell>{person.manager_id ? names[person.manager_id] || '—' : '—'}</TableCell>}
                  {!isMobile && admin && <TableCell align="right">{formatMoney(person.salary)}</TableCell>}
                  {admin && (
                    <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                      {!person.is_archived && (
                        <IconButton size="small" aria-label={t('Edit {name}', { name: fullName(person) })} onClick={() => setDialog({ type: 'edit', person })}>
                          <EditIcon fontSize="small" />
                        </IconButton>
                      )}
                      {!person.is_archived && person.id !== user.id && (
                        <IconButton size="small" aria-label={t('Archive {name}', { name: fullName(person) })} onClick={() => setDialog({ type: 'archive', person })}>
                          <ArchiveIcon fontSize="small" />
                        </IconButton>
                      )}
                      {person.is_archived && (
                        <IconButton size="small" aria-label={t('Restore {name}', { name: fullName(person) })} onClick={() => setDialog({ type: 'restore', person })}>
                          <UnarchiveIcon fontSize="small" />
                        </IconButton>
                      )}
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <Paginator pager={pager} options={[10, 25, 50, 100]} label="People per page:" />
        </TableContainer>
      )}

      {dialog?.type === 'edit' && (
        <UserDialog open user={dialog.person} managers={managers.filter((m) => !m.is_archived)} onClose={close}
          onSaved={(saved) => {
            notify(dialog.person ? t('Saved') : t('Created {name} with username {username}', { name: fullName(saved), username: saved.username }));
            refresh();
          }} />
      )}
      <ConfirmDialog open={dialog?.type === 'archive'} title={t('Archive {name}?', { name: fullName(dialog?.person) })} confirmLabel="Archive" color="error"
        message={t("They'll be signed out and can no longer sign in. Their future booked hours are released. You can restore them later.")}
        onConfirm={async () => { await api(`/users/${dialog.person.id}`, { method: 'DELETE' }); notify(t('Archived')); refresh(); }}
        onClose={close} />
      <ConfirmDialog open={dialog?.type === 'restore'} title={t('Restore {name}?', { name: fullName(dialog?.person) })} confirmLabel="Restore"
        message={t("They'll be able to sign in again.")}
        onConfirm={async () => { await api(`/users/${dialog.person.id}/restore`, { method: 'POST' }); notify(t('Restored')); refresh(); }}
        onClose={close} />
    </>
  );
}
