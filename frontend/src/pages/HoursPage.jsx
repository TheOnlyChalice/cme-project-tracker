import AddIcon from '@mui/icons-material/Add';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import EditIcon from '@mui/icons-material/Edit';
import SearchIcon from '@mui/icons-material/Search';
import {
  Box, Button, Card, CardContent, IconButton, InputAdornment, LinearProgress, Link, MenuItem, Paper, Stack, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, TextField, Typography,
} from '@mui/material';
import PropTypes from 'prop-types';
import { useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { api } from '../api/client.js';
import { useAuth } from '../auth/AuthContext.js';
import CapacityHeatMap from '../components/CapacityHeatMap.jsx';
import CapacityBars from '../components/charts/CapacityBars.jsx';
import ConfirmDialog from '../components/ConfirmDialog.jsx';
import ErrorAlert from '../components/ErrorAlert.jsx';
import AssignHoursDialog from '../components/forms/AssignHoursDialog.jsx';
import Loading from '../components/Loading.jsx';
import { useNotify } from '../components/NotifyContext.js';
import PageHeader from '../components/PageHeader.jsx';
import Paginator from '../components/Paginator.jsx';
import WeekPicker from '../components/WeekPicker.jsx';
import useIsMobile from '../hooks/useIsMobile.js';
import useLoader from '../hooks/useLoader.js';
import usePagination from '../hooks/usePagination.js';
import { useT } from '../i18n/LanguageContext.js';
import { addWeeks, formatDate, formatHours, mondayOf } from '../utils/format.js';
import { canManageProject, isAdmin, isManager } from '../utils/roles.js';

const RANGE_WEEKS = 6;

/** How full a 40-hour week is, as a bar. */
function WeekBar({ assigned }) {
  const t = useT();
  const percent = Math.min((Number(assigned) / 40) * 100, 100);
  return (
    <Box sx={{ minWidth: 140 }}>
      <Typography variant="body2">{t('{hours} of 40 h', { hours: formatHours(assigned) })}</Typography>
      <LinearProgress variant="determinate" value={percent} color={percent >= 100 ? 'secondary' : 'primary'}
        sx={{ height: 10 }} aria-label={t('{percent}% booked', { percent: Math.round(percent) })} />
    </Box>
  );
}

WeekBar.propTypes = {
  assigned: PropTypes.oneOfType([PropTypes.number, PropTypes.string]).isRequired,
};

/** Earlier / later buttons that move the heat map's range of weeks. */
function RangeControls({ start, onChange }) {
  const t = useT();
  const end = addWeeks(start, RANGE_WEEKS - 1);
  return (
    <Stack direction="row" alignItems="center" spacing={1}>
      <IconButton aria-label={t('Earlier weeks')} onClick={() => onChange(addWeeks(start, -4))}><ChevronLeftIcon /></IconButton>
      <Typography variant="body2" sx={{ minWidth: 170, textAlign: 'center' }}>
        {formatDate(start)} – {formatDate(end)}
      </Typography>
      <IconButton aria-label={t('Later weeks')} onClick={() => onChange(addWeeks(start, 4))}><ChevronRightIcon /></IconButton>
    </Stack>
  );
}

RangeControls.propTypes = {
  start: PropTypes.string.isRequired,
  onChange: PropTypes.func.isRequired,
};

// [MY WEEK HERE]
// How: Employees see a strip of their own next six weeks (shaded like the
//      team heat map), then the selected week's bookings: project, milestone,
//      and hours.
// Why: Employees don't log time; their manager plans it. This shows them
//      what's coming and what to work on now.
/** An employee's own booked hours: a six-week strip and one week's detail. */
function MyWeek({ user }) {
  const t = useT();
  const thisWeek = mondayOf();
  const [week, setWeek] = useState(thisWeek);
  const [rangeStart, setRangeStart] = useState(thisWeek);
  const strip = useLoader(() => api('/insights/capacity', { query: { start: rangeStart, weeks: RANGE_WEEKS } }), [rangeStart]);
  const detail = useLoader(() => api(`/users/${user.id}/availability`, { query: { week } }), [user.id, week]);

  return (
    <Stack spacing={3}>
      <PageHeader title={t('My week')} subtitle={t('The hours your manager has planned for you.')} />
      <Card>
        <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 1 }}>
            <Typography variant="h6" component="h2">{t('Coming up')}</Typography>
            <RangeControls start={rangeStart} onChange={setRangeStart} />
          </Box>
          <ErrorAlert error={strip.error} onRetry={strip.reload} />
          {strip.data && (
            <CapacityHeatMap weeks={strip.data.weeks} people={strip.data.people} currentWeek={thisWeek}
              selectedWeek={week} onSelectWeek={setWeek} />
          )}
        </CardContent>
      </Card>
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 1, mb: 2 }}>
            <Typography variant="h6" component="h2">{t('Week of {date}', { date: formatDate(week) })}</Typography>
            <WeekPicker week={week} onChange={setWeek} />
          </Box>
          <ErrorAlert error={detail.error} onRetry={detail.reload} />
          {detail.loading && !detail.data && <Loading />}
          {detail.data && (
            <>
              <WeekBar assigned={detail.data.assigned} />
              <Typography color="text.secondary" sx={{ mt: 1, mb: 2 }}>{t('{hours} not yet assigned', { hours: formatHours(detail.data.available) })}</Typography>
              {detail.data.assignments.length === 0 && <Typography color="text.secondary">{t('Nothing booked this week.')}</Typography>}
              <Stack spacing={1}>
                {detail.data.assignments.map((a) => (
                  <Box key={a.assignment_id} sx={{ display: 'flex', justifyContent: 'space-between', gap: 2, borderTop: 1, borderColor: 'divider', pt: 1 }}>
                    <Box>
                      <Typography sx={{ fontWeight: 600 }}>{a.project_name}</Typography>
                      <Typography variant="body2" color="text.secondary">{a.milestone_name}</Typography>
                    </Box>
                    <Typography sx={{ fontWeight: 600 }}>{formatHours(a.hours)}</Typography>
                  </Box>
                ))}
              </Stack>
            </>
          )}
        </CardContent>
      </Card>
    </Stack>
  );
}

MyWeek.propTypes = {
  user: PropTypes.object.isRequired,
};

// [TEAM PLANNER HERE]
// How: Managers (and admins) see the capacity heat map for six weeks, then
//      the bookings for the selected week (click a heat map cell or use the
//      week arrows), and can add, change, or remove hours on projects they
//      manage.
// Why: Answers "how are resources allocated", "who has spare capacity", and
//      "who is over-booked" across weeks, and is where the 40-hour rule is
//      applied: free hours show up front and the backend refuses anything over 40.
/** Managers' heat map of team capacity plus the selected week's bookings. */
function TeamPlanner({ user }) {
  const t = useT();
  const notify = useNotify();
  const isMobile = useIsMobile();
  const thisWeek = mondayOf();
  const [week, setWeek] = useState(thisWeek);
  const [rangeStart, setRangeStart] = useState(addWeeks(thisWeek, -1));
  const [dialog, setDialog] = useState(null);

  const grid = useLoader(() => api('/insights/capacity', { query: { start: rangeStart, weeks: RANGE_WEEKS } }), [rangeStart]);
  const bookings = useLoader(() => api('/hour-assignments', { query: { week } }).then((d) => d.assignments), [week]);
  const reference = useLoader(async () => {
    const [projects, users, managerList] = await Promise.all([
      api('/projects', { query: { status: 'active' } }),
      api('/users', { query: { role: 'employee' } }),
      api('/users', { query: { role: 'manager' } }),
    ]);
    const lists = await Promise.all(projects.projects.map((p) => api(`/projects/${p.id}/milestones`)));
    const milestones = Object.fromEntries(lists.flatMap((l) => l.milestones).map((m) => [m.id, m]));
    return { projects: projects.projects, employees: users.users, managers: managerList.users, milestones };
  }, []);

  // [HEAT MAP FILTERS AND PAGING HERE]
  // How: Above the heat map, a name search and (for admins) a manager filter
  //      narrow the rows; the map then shows 15 people per page, and the
  //      bookings table below shows 15 bookings per page.
  // Why: Admins see 70+ employees; filtering to one team or finding one
  //      person, then paging, keeps the grid readable.
  const [nameFilter, setNameFilter] = useState('');
  const [managerFilter, setManagerFilter] = useState('');
  const heatRows = (grid.data?.people || []).filter((person) =>
    person.name.toLowerCase().includes(nameFilter.trim().toLowerCase())
    && (!managerFilter || person.manager_id === managerFilter));
  const heatPager = usePagination(heatRows, 15);
  const bookingPager = usePagination(bookings.data, 15);

  const reloadAll = () => {
    grid.reload();
    bookings.reload();
    reference.reload();
  };
  const pickWeek = (next) => {
    setWeek(next);
    if (next < rangeStart || next > addWeeks(rangeStart, RANGE_WEEKS - 1)) setRangeStart(addWeeks(next, -1));
  };

  if (reference.loading && !reference.data) return <Loading label="Loading team hours" />;
  if (reference.error) return <ErrorAlert error={reference.error} onRetry={reference.reload} />;

  const { projects, employees, milestones } = reference.data;
  const projectsById = Object.fromEntries(projects.map((p) => [p.id, p]));
  const names = Object.fromEntries(employees.map((e) => [e.id, `${e.first_name} ${e.last_name}`]));
  const manageable = projects.filter((p) => canManageProject(user, p));
  const close = () => setDialog(null);

  return (
    <Stack spacing={3}>
      <PageHeader
        title={t('Team hours')}
        subtitle={t('Every employee has 40 hours a week, reset each Monday.')}
        actions={manageable.length > 0 && (
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialog({ type: 'assign' })}>{t('Assign hours')}</Button>
        )}
      />

      <Card>
        <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 1 }}>
            <Box>
              <Typography variant="h6" component="h2">{t('Capacity heat map')}</Typography>
              <Typography variant="body2" color="text.secondary">{t('Click a week to see its bookings.')}</Typography>
            </Box>
            <RangeControls start={rangeStart} onChange={setRangeStart} />
          </Box>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
            <TextField label={t('Find a person')} value={nameFilter} onChange={(e) => setNameFilter(e.target.value)}
              sx={{ maxWidth: { sm: 280 } }}
              slotProps={{ input: { startAdornment: <InputAdornment position="start"><SearchIcon /></InputAdornment> } }} />
            {isAdmin(user) && (
              <TextField select label={t('Team')} value={managerFilter} onChange={(e) => setManagerFilter(e.target.value)} sx={{ maxWidth: { sm: 260 } }}>
                <MenuItem value="">{t('All teams')}</MenuItem>
                {(reference.data?.managers || []).map((m) => (
                  <MenuItem key={m.id} value={m.id}>{t("{name}'s team", { name: `${m.first_name} ${m.last_name}` })}</MenuItem>
                ))}
              </TextField>
            )}
          </Stack>
          <ErrorAlert error={grid.error} onRetry={grid.reload} />
          {grid.loading && !grid.data && <Loading />}
          {grid.data && heatRows.length === 0 && (
            <Typography color="text.secondary">{grid.data.people.length ? t('Nobody matches.') : t('No employees on your team yet.')}</Typography>
          )}
          {grid.data && heatRows.length > 0 && (
            <>
              <CapacityBars weeks={grid.data.weeks} people={heatRows} selectedWeek={week} onSelectWeek={pickWeek} />
              <CapacityHeatMap weeks={grid.data.weeks} people={heatPager.pageItems} currentWeek={thisWeek}
                selectedWeek={week} onSelectWeek={pickWeek} linkPeople />
              <Paginator pager={heatPager} options={[15, 30, 60]} label="People per page:" />
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 1, mb: 2 }}>
            <Typography variant="h6" component="h2">{t('Bookings for the week of {date}', { date: formatDate(week) })}</Typography>
            <WeekPicker week={week} onChange={pickWeek} />
          </Box>
          <ErrorAlert error={bookings.error} onRetry={bookings.reload} />
          {bookings.data && bookings.data.length === 0 && <Typography color="text.secondary">{t('No hours booked this week.')}</Typography>}
          {bookings.data && bookings.data.length > 0 && (
            <TableContainer component={Paper} variant="outlined">
              <Table size="small" aria-label={t('Bookings this week')}>
                <TableHead>
                  <TableRow>
                    <TableCell>{t('Person')}</TableCell>
                    {!isMobile && <TableCell>{t('Project')}</TableCell>}
                    <TableCell>{t('Milestone')}</TableCell>
                    <TableCell align="right">{t('Hours')}</TableCell>
                    <TableCell align="right">{t('Actions')}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {bookingPager.pageItems.map((a) => {
                    const project = projectsById[a.project_id];
                    const editable = project && canManageProject(user, project) && a.week_start >= thisWeek;
                    return (
                      <TableRow key={a.id}>
                        <TableCell>
                          {names[a.user_id]
                            ? <Link component={RouterLink} to={`/people/${a.user_id}`} underline="hover" color="inherit">{names[a.user_id]}</Link>
                            : t('Employee')}
                        </TableCell>
                        {!isMobile && <TableCell>{project?.name || '—'}</TableCell>}
                        <TableCell>{milestones[a.milestone_id]?.name || '—'}</TableCell>
                        <TableCell align="right">{formatHours(a.hours)}</TableCell>
                        <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                          {editable && (
                            <>
                              <IconButton size="small" aria-label={t('Change hours')} onClick={() => setDialog({ type: 'assign', assignment: a })}><EditIcon fontSize="small" /></IconButton>
                              <IconButton size="small" aria-label={t('Remove hours')} onClick={() => setDialog({ type: 'remove', assignment: a })}><DeleteOutlineIcon fontSize="small" /></IconButton>
                            </>
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
              <Paginator pager={bookingPager} options={[15, 30, 60]} />
            </TableContainer>
          )}
        </CardContent>
      </Card>

      {dialog?.type === 'assign' && (
        <AssignHoursDialog open
          employees={employees.filter((e) => !e.is_archived)}
          projects={manageable}
          assignment={dialog.assignment}
          defaultWeek={week}
          onClose={close}
          onSaved={() => { notify(t('Hours saved')); reloadAll(); }} />
      )}
      <ConfirmDialog open={dialog?.type === 'remove'} title={t('Remove these hours?')} confirmLabel="Remove" color="error"
        message={t('{name} gets {hours} back for that week.', { name: names[dialog?.assignment?.user_id] || t('This person'), hours: formatHours(dialog?.assignment?.hours) })}
        onConfirm={async () => { await api(`/hour-assignments/${dialog.assignment.id}`, { method: 'DELETE' }); notify(t('Hours removed')); reloadAll(); }}
        onClose={close} />
    </Stack>
  );
}

TeamPlanner.propTypes = {
  user: PropTypes.object.isRequired,
};

/** Team planner for managers and admins; "My week" for employees. */
export default function HoursPage() {
  const { user } = useAuth();
  return isManager(user) ? <TeamPlanner user={user} /> : <MyWeek user={user} />;
}
