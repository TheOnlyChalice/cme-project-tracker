import AddIcon from '@mui/icons-material/Add';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import EditIcon from '@mui/icons-material/Edit';
import {
  Box, Button, Card, CardContent, IconButton, LinearProgress, Paper, Stack, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, Typography,
} from '@mui/material';
import { useState } from 'react';
import PropTypes from 'prop-types';
import { api } from '../api/client.js';
import { useAuth } from '../auth/AuthContext.js';
import ConfirmDialog from '../components/ConfirmDialog.jsx';
import ErrorAlert from '../components/ErrorAlert.jsx';
import AssignHoursDialog from '../components/forms/AssignHoursDialog.jsx';
import Loading from '../components/Loading.jsx';
import { useNotify } from '../components/NotifyContext.js';
import PageHeader from '../components/PageHeader.jsx';
import StatusChip from '../components/StatusChip.jsx';
import WeekPicker from '../components/WeekPicker.jsx';
import useIsMobile from '../hooks/useIsMobile.js';
import useLoader from '../hooks/useLoader.js';
import { useT } from '../i18n/LanguageContext.js';
import { formatHours, mondayOf } from '../utils/format.js';
import { canManageProject, isManager } from '../utils/roles.js';

/** How full a 40-hour week is, as a bar. */
function WeekBar({ assigned }) {
  const t = useT();
  const percent = Math.min((Number(assigned) / 40) * 100, 100);
  return (
    <Box sx={{ minWidth: 140 }}>
      <Typography variant="body2">{t('{hours} of 40 h', { hours: formatHours(assigned) })}</Typography>
      <LinearProgress variant="determinate" value={percent} color={percent >= 100 ? 'error' : 'primary'}
        sx={{ height: 8, borderRadius: 4 }} aria-label={t('{percent}% booked', { percent: Math.round(percent) })} />
    </Box>
  );
}

// [MY WEEK HERE]
// How: Employees see their own 40 hours for the chosen week: how much is
//      booked and on which project and milestone.
// Why: Employees don't log time; their manager plans it. This shows them
//      what they've been assigned to work on.
/** An employee's own booked hours for one week. */
function MyWeek({ user, week, setWeek }) {
  const t = useT();
  const { data, loading, error, reload } = useLoader(
    () => api(`/users/${user.id}/availability`, { query: { week } }), [user.id, week]);
  return (
    <>
      <PageHeader title={t('My week')} subtitle={t('The hours your manager has planned for you.')} actions={<WeekPicker week={week} onChange={setWeek} />} />
      <ErrorAlert error={error} onRetry={reload} />
      {loading && !data && <Loading />}
      {data && (
        <Card>
          <CardContent>
            <WeekBar assigned={data.assigned} />
            <Typography color="text.secondary" sx={{ mt: 1, mb: 2 }}>{t('{hours} not yet assigned', { hours: formatHours(data.available) })}</Typography>
            {data.assignments.length === 0 && <Typography color="text.secondary">{t('Nothing booked this week.')}</Typography>}
            <Stack spacing={1}>
              {data.assignments.map((a) => (
                <Box key={a.assignment_id} sx={{ display: 'flex', justifyContent: 'space-between', gap: 2, borderTop: 1, borderColor: 'divider', pt: 1 }}>
                  <Box>
                    <Typography fontWeight={600}>{a.project_name}</Typography>
                    <Typography variant="body2" color="text.secondary">{a.milestone_name}</Typography>
                  </Box>
                  <Typography>{formatHours(a.hours)}</Typography>
                </Box>
              ))}
            </Stack>
          </CardContent>
        </Card>
      )}
    </>
  );
}

// [TEAM PLANNER HERE]
// How: Managers (and admins) see each employee's booked and free hours for
//      the week, then every booking, and can add, change, or remove hours
//      on projects they manage.
// Why: Answers "how are resources allocated" and "who has spare capacity",
//      and is where the 40-hour rule is applied in practice: the planner
//      shows free hours up front and the backend refuses anything over 40.
/** Managers' weekly view of team capacity and bookings. */
function TeamPlanner({ user, week, setWeek }) {
  const t = useT();
  const notify = useNotify();
  const isMobile = useIsMobile();
  const [dialog, setDialog] = useState(null);

  const { data, loading, error, reload } = useLoader(async () => {
    const [utilization, assignments, projects, users] = await Promise.all([
      api('/insights/utilization', { query: { week } }),
      api('/hour-assignments', { query: { week } }),
      api('/projects', { query: { status: 'active' } }),
      api('/users', { query: { role: 'employee' } }),
    ]);
    const lists = await Promise.all(projects.projects.map((p) => api(`/projects/${p.id}/milestones`)));
    const milestones = Object.fromEntries(lists.flatMap((l) => l.milestones).map((m) => [m.id, m]));
    return {
      people: utilization.employees,
      assignments: assignments.assignments,
      projects: projects.projects,
      employees: users.users,
      milestones,
    };
  }, [week]);

  if (loading && !data) return <Loading label="Loading team hours" />;
  if (error) return <ErrorAlert error={error} onRetry={reload} />;

  const projectsById = Object.fromEntries(data.projects.map((p) => [p.id, p]));
  const names = Object.fromEntries(data.people.map((p) => [p.user_id, p.name]));
  const manageable = data.projects.filter((p) => canManageProject(user, p));
  const close = () => setDialog(null);

  return (
    <>
      <PageHeader
        title={t('Team hours')}
        subtitle={t('Every employee has 40 hours a week, reset each Monday.')}
        actions={(
          <>
            <WeekPicker week={week} onChange={setWeek} />
            {manageable.length > 0 && <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialog({ type: 'assign' })}>{t('Assign hours')}</Button>}
          </>
        )}
      />

      <Typography variant="h6" component="h2" sx={{ mb: 1 }}>{t("Who's available")}</Typography>
      {data.people.length === 0 && <Typography color="text.secondary" sx={{ mb: 3 }}>{t('No employees on your team yet.')}</Typography>}
      <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', lg: 'repeat(3, 1fr)' }, mb: 4 }}>
        {data.people.map((person) => (
          <Card key={person.user_id}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                <Typography fontWeight={600}>{person.name}</Typography>
                <StatusChip value={person.state} />
              </Box>
              <WeekBar assigned={person.assigned} />
              {person.projects.map((p) => (
                <Typography key={p.project_id} variant="body2" color="text.secondary">
                  {p.project_name}: {formatHours(p.hours)}
                </Typography>
              ))}
            </CardContent>
          </Card>
        ))}
      </Box>

      <Typography variant="h6" component="h2" sx={{ mb: 1 }}>{t('Bookings this week')}</Typography>
      {data.assignments.length === 0 && <Typography color="text.secondary">{t('No hours booked this week.')}</Typography>}
      {data.assignments.length > 0 && (
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
              {data.assignments.map((a) => {
                const project = projectsById[a.project_id];
                const editable = project && canManageProject(user, project) && a.week_start >= mondayOf();
                return (
                  <TableRow key={a.id}>
                    <TableCell>{names[a.user_id] || t('Employee')}</TableCell>
                    {!isMobile && <TableCell>{project?.name || '—'}</TableCell>}
                    <TableCell>{data.milestones[a.milestone_id]?.name || '—'}</TableCell>
                    <TableCell align="right">{formatHours(a.hours)}</TableCell>
                    <TableCell align="right">
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
        </TableContainer>
      )}

      {dialog?.type === 'assign' && (
        <AssignHoursDialog open
          employees={data.employees.filter((e) => !e.is_archived)}
          projects={manageable}
          assignment={dialog.assignment}
          defaultWeek={week}
          onClose={close}
          onSaved={() => { notify(t('Hours saved')); reload(); }} />
      )}
      <ConfirmDialog open={dialog?.type === 'remove'} title={t('Remove these hours?')} confirmLabel="Remove" color="error"
        message={t('{name} gets {hours} back for that week.', { name: names[dialog?.assignment?.user_id] || t('This person'), hours: formatHours(dialog?.assignment?.hours) })}
        onConfirm={async () => { await api(`/hour-assignments/${dialog.assignment.id}`, { method: 'DELETE' }); notify(t('Hours removed')); reload(); }}
        onClose={close} />
    </>
  );
}

/** Team planner for managers and admins; "My week" for employees. */
export default function HoursPage() {
  const { user } = useAuth();
  const [week, setWeek] = useState(mondayOf());
  return isManager(user)
    ? <TeamPlanner user={user} week={week} setWeek={setWeek} />
    : <MyWeek user={user} week={week} setWeek={setWeek} />;
}

WeekBar.propTypes = {
  assigned: PropTypes.oneOfType([PropTypes.number, PropTypes.string]).isRequired,
};

MyWeek.propTypes = {
  user: PropTypes.object.isRequired,
  week: PropTypes.string.isRequired,
  setWeek: PropTypes.func.isRequired,
};

TeamPlanner.propTypes = {
  user: PropTypes.object.isRequired,
  week: PropTypes.string.isRequired,
  setWeek: PropTypes.func.isRequired,
};
