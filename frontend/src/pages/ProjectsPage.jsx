import AddIcon from '@mui/icons-material/Add';
import SearchIcon from '@mui/icons-material/Search';
import {
  Box, Button, Card, CardActionArea, CardContent, FormControlLabel, InputAdornment, MenuItem, Paper,
  Stack, Switch, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField, Typography,
} from '@mui/material';
import { useState } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import { api } from '../api/client.js';
import { useAuth } from '../auth/AuthContext.js';
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
import { isAdmin } from '../utils/roles.js';

// [PROJECT LIST HERE]
// How: Lists the projects the backend says this user may see, with search,
//      a status filter, and (for admins) an "include archived" switch. The
//      filters are sent to the API, which applies them after its own
//      visibility rules.
// Why: Covers the search-and-filter requirement while making sure no filter
//      can reveal a project the user isn't allowed to see.
/** Searchable list of the projects the user can see. */
export default function ProjectsPage() {
  const { user } = useAuth();
  const admin = isAdmin(user);
  const isMobile = useIsMobile();
  const navigate = useNavigate();
  const notify = useNotify();
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState(admin ? '' : 'active');
  const [archived, setArchived] = useState(false);
  const [creating, setCreating] = useState(false);
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
        title="Projects"
        subtitle={admin ? 'Every project in the company.' : user.role === 'manager' ? 'Projects you manage.' : "Your team's active projects."}
        actions={admin && <Button variant="contained" startIcon={<AddIcon />} onClick={() => setCreating(true)}>New project</Button>}
      />

      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 2 }} alignItems={{ sm: 'center' }}>
        <TextField
          label="Search projects"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          sx={{ maxWidth: { sm: 320 } }}
          slotProps={{ input: { startAdornment: <InputAdornment position="start"><SearchIcon /></InputAdornment> } }}
        />
        {admin && (
          <>
            <TextField select label="Status" value={status} onChange={(event) => setStatus(event.target.value)} sx={{ maxWidth: { sm: 180 } }}>
              <MenuItem value="">All statuses</MenuItem>
              <MenuItem value="active">Active</MenuItem>
              <MenuItem value="completed">Completed</MenuItem>
              <MenuItem value="abandoned">Abandoned</MenuItem>
            </TextField>
            <FormControlLabel control={<Switch checked={archived} onChange={(e) => setArchived(e.target.checked)} />} label="Include archived" />
          </>
        )}
      </Stack>

      <ErrorAlert error={error} onRetry={reload} />
      {loading && !data && <Loading label="Loading projects" />}
      {data && data.projects.length === 0 && (
        <Typography color="text.secondary" sx={{ py: 4 }}>No projects match.</Typography>
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
                    label={`${formatHours(p.hours_assigned)} of ${p.allocated_hours} h`} />
                </CardContent>
              </CardActionArea>
            </Card>
          ))}
        </Stack>
      ) : (
        <TableContainer component={Paper} variant="outlined">
          <Table size="small" aria-label="Projects">
            <TableHead>
              <TableRow>
                <TableCell>Project</TableCell>
                <TableCell>Manager</TableCell>
                <TableCell>Dates</TableCell>
                <TableCell>Hours</TableCell>
                <TableCell>Status</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data.projects.map((p) => (
                <TableRow key={p.id} hover sx={{ cursor: 'pointer' }} onClick={() => navigate(`/projects/${p.id}`)}>
                  <TableCell>
                    <Typography fontWeight={600}>{p.name}</Typography>
                    <Typography variant="body2" color="text.secondary" noWrap sx={{ maxWidth: 320 }}>{p.description}</Typography>
                  </TableCell>
                  <TableCell>{people[p.manager_id] ? fullName(people[p.manager_id]) : '—'}</TableCell>
                  <TableCell>{formatDate(p.start_date)} – {formatDate(p.end_date)}</TableCell>
                  <TableCell>
                    <ProgressCell value={(Number(p.hours_assigned) / p.allocated_hours) * 100}
                      label={`${formatHours(p.hours_assigned)} of ${p.allocated_hours} h`} />
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

      {creating && (
        <ProjectDialog
          open
          managers={managers}
          canPickManager
          onClose={() => setCreating(false)}
          onSaved={(project) => {
            notify(`Created "${project.name}"`);
            navigate(`/projects/${project.id}`);
          }}
        />
      )}
    </>
  );
}
