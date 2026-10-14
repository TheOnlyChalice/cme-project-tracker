import AddIcon from '@mui/icons-material/Add';
import AutoDeleteIcon from '@mui/icons-material/AutoDeleteOutlined';
import SearchIcon from '@mui/icons-material/Search';
import {
  Box, Button, Card, CardActionArea, CardContent, FormControlLabel, InputAdornment, MenuItem, Paper,
  Stack, Switch, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField, Typography,
} from '@mui/material';
import { useState } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import { api } from '../api/client.js';
import { useAuth } from '../auth/AuthContext.js';
import ConfirmDialog from '../components/ConfirmDialog.jsx';
import ErrorAlert from '../components/ErrorAlert.jsx';
import ProjectDialog from '../components/forms/ProjectDialog.jsx';
import Loading from '../components/Loading.jsx';
import { useNotify } from '../components/NotifyContext.js';
import PageHeader from '../components/PageHeader.jsx';
import ProgressCell from '../components/ProgressCell.jsx';
import StatusChip from '../components/StatusChip.jsx';
import useDebouncedValue from '../hooks/useDebouncedValue.js';
import useIsMobile from '../hooks/useIsMobile.js';
import useLoader from '../hooks/useLoader.js';
import { formatDate, formatHours, fullName } from '../utils/format.js';
import { useT } from '../i18n/LanguageContext.js';
import { isAdmin } from '../utils/roles.js';

// [PROJECT LIST HERE]
// How: Lists the projects the backend says this user may see, with search,
//      a status filter, and (for admins) an "include archived" switch. The
//      filters are sent to the API, which applies them after its own
//      visibility rules.
// Why: Covers the search-and-filter requirement while making sure no filter
//      can reveal a project the user isn't allowed to see.
/** Searchable list of the projects the user can see. */
/** Searchable list of the projects the user can see. */
export default function ProjectsPage() {
  const { user } = useAuth();
  const t = useT();
  const admin = isAdmin(user);
  const isMobile = useIsMobile();
  const navigate = useNavigate();
  const notify = useNotify();
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState(admin ? '' : 'active');
  const [archived, setArchived] = useState(false);
  const [creating, setCreating] = useState(false);
  const [sweeping, setSweeping] = useState(false);
  const query = useDebouncedValue(search);

  const { data, loading, error, reload } = useLoader(async () => {
    const [projects, users] = await Promise.all([
      api('/projects', { query: { search: query, status, include_archived: archived ? 'true' : '' } }),
      api('/users'),
    ]);
    return { projects: projects.projects, users: users.users };
  }, [query, status, archived]);

  const people = Object.fromEntries((data?.users || []).map((u) => [u.id, u]));
  const managers = (data?.users || []).filter((u) => u.role !== 'employee' && !u.is_archived);

  return (
    <>
      <PageHeader
        title={t('Projects')}
        subtitle={admin ? t('Every project in the company.') : user.role === 'manager' ? t('Projects you manage.') : t("Your team's active projects.")}
        actions={admin && (
          <>
            <Button startIcon={<AutoDeleteIcon />} onClick={() => setSweeping(true)}>{t('Archive inactive now')}</Button>
            <Button variant="contained" startIcon={<AddIcon />} onClick={() => setCreating(true)}>{t('New project')}</Button>
          </>
        )}
      />

      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 2 }} alignItems={{ sm: 'center' }}>
        <TextField
          label={t('Search projects')}
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          sx={{ maxWidth: { sm: 320 } }}
          slotProps={{ input: { startAdornment: <InputAdornment position="start"><SearchIcon /></InputAdornment> } }}
        />
        {admin && (
          <>
            <TextField select label={t('Status')} value={status} onChange={(event) => setStatus(event.target.value)} sx={{ maxWidth: { sm: 180 } }}>
              <MenuItem value="">{t('All statuses')}</MenuItem>
              <MenuItem value="active">{t('Active')}</MenuItem>
              <MenuItem value="completed">{t('Completed')}</MenuItem>
              <MenuItem value="abandoned">{t('Abandoned')}</MenuItem>
            </TextField>
            <FormControlLabel control={<Switch checked={archived} onChange={(e) => setArchived(e.target.checked)} />} label={t('Include archived')} />
          </>
        )}
      </Stack>

      <ErrorAlert error={error} onRetry={reload} />
      {loading && !data && <Loading label="Loading projects" />}
      {data && data.projects.length === 0 && (
        <Typography color="text.secondary" sx={{ py: 4 }}>{t('No projects match.')}</Typography>
      )}

      {data && data.projects.length > 0 && (isMobile ? (
        <Stack spacing={2}>
          {data.projects.map((p) => (
            <Card key={p.id}>
              <CardActionArea component={RouterLink} to={`/projects/${p.id}`}>
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 1 }}>
                    <Typography fontWeight={600}>{p.name}</Typography>
                    <StatusChip value={p.status} archived={p.is_archived && p.status === 'active'} />
                  </Box>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    {formatDate(p.start_date)} – {formatDate(p.end_date)}
                  </Typography>
                  <ProgressCell value={(Number(p.hours_assigned) / p.allocated_hours) * 100}
                    label={t('{used} of {total} h', { used: formatHours(p.hours_assigned), total: p.allocated_hours })} />
                </CardContent>
              </CardActionArea>
            </Card>
          ))}
        </Stack>
      ) : (
        <TableContainer component={Paper} variant="outlined">
          <Table size="small" aria-label={t('Projects')}>
            <TableHead>
              <TableRow>
                <TableCell>{t('Project')}</TableCell>
                <TableCell>{t('Manager')}</TableCell>
                <TableCell>{t('Dates')}</TableCell>
                <TableCell>{t('Hours')}</TableCell>
                <TableCell>{t('Status')}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data.projects.map((p) => (
                <TableRow
                  key={p.id}
                  hover
                  sx={{ cursor: 'pointer' }}
                  // [ROW CLICK VS TEXT SELECT HERE]
                  // How: Clicking a row opens the project, unless the user just
                  //      selected some text in it.
                  // Why: Lets people copy names and descriptions from the table
                  //      without being whisked away to the project page.
                  onClick={() => {
                    if (!window.getSelection()?.toString()) navigate(`/projects/${p.id}`);
                  }}
                >
                  <TableCell>
                    <Typography fontWeight={600}>{p.name}</Typography>
                    <Typography variant="body2" color="text.secondary" noWrap sx={{ maxWidth: 320 }}>{p.description}</Typography>
                  </TableCell>
                  <TableCell>{people[p.manager_id] ? fullName(people[p.manager_id]) : '—'}</TableCell>
                  <TableCell>{formatDate(p.start_date)} – {formatDate(p.end_date)}</TableCell>
                  <TableCell>
                    <ProgressCell value={(Number(p.hours_assigned) / p.allocated_hours) * 100}
                      label={t('{used} of {total} h', { used: formatHours(p.hours_assigned), total: p.allocated_hours })} />
                  </TableCell>
                  <TableCell>
                    <Stack direction="row" spacing={0.5}>
                      <StatusChip value={p.status} />
                      {p.is_archived && p.status === 'active' && <StatusChip archived />}
                    </Stack>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      ))}

      {/* [ARCHIVE INACTIVE BUTTON HERE]
          How: Admins can run the two-week inactivity rule immediately; the
               result says how many projects were archived.
          Why: The rule also runs by itself every hour, but this lets admins
               apply it on demand (useful for demos and clean-ups). */}
      <ConfirmDialog
        open={sweeping}
        title={t('Archive inactive projects now?')}
        message={t('Projects with no activity for 14 days and no upcoming hours will be archived. Admins can restore them.')}
        confirmLabel="Archive"
        color="warning"
        onConfirm={async () => {
          const result = await api('/admin/maintenance', { method: 'POST' });
          notify(t('{count} projects archived', { count: result.archived.length }));
          reload();
        }}
        onClose={() => setSweeping(false)}
      />
      {creating && (
        <ProjectDialog
          open
          managers={managers}
          canPickManager
          onClose={() => setCreating(false)}
          onSaved={(project) => {
            notify(t('Created "{name}"', { name: project.name }));
            navigate(`/projects/${project.id}`);
          }}
        />
      )}
    </>
  );
}
