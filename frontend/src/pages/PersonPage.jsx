import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import {
  Avatar, Box, Breadcrumbs, Button, Card, CardContent, Link, Stack, Typography,
} from '@mui/material';
import PropTypes from 'prop-types';
import { useState } from 'react';
import { Link as RouterLink, useParams } from 'react-router-dom';
import { api } from '../api/client.js';
import { useAuth } from '../auth/AuthContext.js';
import CapacityHeatMap from '../components/CapacityHeatMap.jsx';
import ErrorAlert from '../components/ErrorAlert.jsx';
import AssignHoursDialog from '../components/forms/AssignHoursDialog.jsx';
import UserDialog from '../components/forms/UserDialog.jsx';
import Loading from '../components/Loading.jsx';
import { useNotify } from '../components/NotifyContext.js';
import StatusChip from '../components/StatusChip.jsx';
import useLoader from '../hooks/useLoader.js';
import { useT } from '../i18n/LanguageContext.js';
import { addWeeks, formatDate, formatHours, formatMoney, fullName, mondayOf } from '../utils/format.js';
import { isAdmin, isManager } from '../utils/roles.js';

/** One label/value row in the details card. */
function Row({ label, children }) {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2, py: 1, borderBottom: 1, borderColor: 'divider' }}>
      <Typography color="text.secondary">{label}</Typography>
      <Box sx={{ textAlign: 'right', fontWeight: 600, minWidth: 0 }}>{children}</Box>
    </Box>
  );
}

Row.propTypes = {
  label: PropTypes.node.isRequired,
  children: PropTypes.node,
};

// [PERSON PAGE HERE]
// How: One page per person, opened by clicking a name almost anywhere (the
//      People directory, the heat map, milestone chips, a project's manager,
//      the audit log). It shows their role, job, manager (or team, for
//      managers), current projects, and their next six weeks of hours with
//      the selected week's bookings. Managers can assign this person's hours
//      from here, and admins can edit the person. The backend only returns
//      people the viewer may see, so everyone else gets "not found".
// Why: Questions about a person ("what is Sam working on, and are they
//      free next week?") get answered in one place instead of four.
/** A person's details, projects, and upcoming hours. */
export default function PersonPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const t = useT();
  const notify = useNotify();
  const thisWeek = mondayOf();
  const [week, setWeek] = useState(thisWeek);
  const [dialog, setDialog] = useState(null);

  const main = useLoader(async () => {
    const person = await api(`/users/${id}`);
    const [projects, users, team] = await Promise.all([
      api('/projects', { query: { status: 'active' } }),
      api('/users'),
      person.role !== 'employee' && (isAdmin(user) || user.id === person.id)
        ? api(`/users/${id}/team`).then((d) => d.users)
        : Promise.resolve([]),
    ]);
    return { person, projects: projects.projects, users: users.users, team };
  }, [id, user.id]);
  const strip = useLoader(async () => {
    const grid = await api('/insights/capacity', { query: { start: thisWeek, weeks: 6 } });
    return { weeks: grid.weeks, people: grid.people.filter((p) => p.user_id === id) };
  }, [id]);
  const detail = useLoader(() => api(`/users/${id}/availability`, { query: { week } }), [id, week]);

  if (main.loading && !main.data) return <Loading />;
  if (main.error) {
    return main.error.status === 404 ? (
      <Box sx={{ py: 6, textAlign: 'center' }}>
        <Typography variant="h6">{t('Person not found')}</Typography>
        <Typography color="text.secondary" sx={{ mb: 2 }}>{t('They may be archived or outside your access.')}</Typography>
        <Button component={RouterLink} to="/">{t('Back to dashboard')}</Button>
      </Box>
    ) : <ErrorAlert error={main.error} onRetry={main.reload} />;
  }

  const { person, projects, users, team } = main.data;
  const names = Object.fromEntries(users.map((u) => [u.id, u]));
  const projectNames = Object.fromEntries(projects.map((p) => [p.id, p]));
  const manager = person.manager_id ? names[person.manager_id] : null;
  const canAssign = person.role === 'employee' && !person.is_archived
    && (isAdmin(user) || (user.role === 'manager' && person.manager_id === user.id));
  const assignable = projects.filter((p) => p.manager_id === person.manager_id);
  const managerUsers = users.filter((u) => u.role !== 'employee' && !u.is_archived);
  const refresh = () => {
    main.reload();
    strip.reload();
    detail.reload();
  };

  return (
    <Stack spacing={3}>
      <Breadcrumbs aria-label={t('Breadcrumb')}>
        {isManager(user)
          ? <Link component={RouterLink} to="/people" underline="hover" color="inherit">{t('People')}</Link>
          : <Link component={RouterLink} to="/" underline="hover" color="inherit">{t('Dashboard')}</Link>}
        <Typography color="text.primary">{fullName(person)}</Typography>
      </Breadcrumbs>

      <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 2 }}>
        <Avatar src={person.profile_picture_url || undefined}
          sx={{ width: 64, height: 64, fontSize: 24, fontWeight: 600, bgcolor: 'secondary.main', color: 'secondary.contrastText' }}>
          {person.first_name[0]}{person.last_name[0]}
        </Avatar>
        <Box sx={{ flexGrow: 1, minWidth: 200 }}>
          <Typography variant="h5" component="h1">{fullName(person)}</Typography>
          <Typography color="text.secondary">{person.job_title || t('Not set')} · <code>{person.username}</code></Typography>
        </Box>
        <StatusChip value={person.role} />
        {person.is_archived && <StatusChip archived />}
        {canAssign && <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialog('assign')}>{t('Assign hours')}</Button>}
        {isAdmin(user) && !person.is_archived && <Button startIcon={<EditIcon />} onClick={() => setDialog('edit')}>{t('Edit')}</Button>}
      </Box>

      <Box sx={{ display: 'grid', gap: 3, gridTemplateColumns: { xs: '1fr', md: 'repeat(2, minmax(0, 1fr))' } }}>
        <Card>
          <CardContent>
            <Typography variant="h6" component="h2" gutterBottom>{t('Details')}</Typography>
            <Row label={t('Email')}>{person.email}</Row>
            {person.role === 'employee' && (
              <Row label={t('Reports to')}>
                {manager
                  ? (isAdmin(user) || manager.id === user.id
                    ? <Link component={RouterLink} to={`/people/${manager.id}`} underline="hover">{fullName(manager)}</Link>
                    : fullName(manager))
                  : person.manager_name || '—'}
              </Row>
            )}
            {'salary' in person && <Row label={t('Salary')}>{formatMoney(person.salary)}</Row>}
            <Row label={t('Member since')}>{formatDate(person.created_at)}</Row>
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <Typography variant="h6" component="h2" gutterBottom>
              {person.role === 'employee' ? t('Current projects') : t('Projects managed')}
            </Typography>
            {person.current_project_ids.length === 0 && <Typography color="text.secondary">{t('No active projects.')}</Typography>}
            <Stack spacing={0.75}>
              {person.current_project_ids.map((pid) => (
                <Link key={pid} component={RouterLink} to={`/projects/${pid}`} underline="hover" sx={{ fontWeight: 600 }}>
                  {projectNames[pid]?.name || t('Project')}
                </Link>
              ))}
            </Stack>
            {team.length > 0 && (
              <>
                <Typography variant="subtitle1" sx={{ mt: 2, mb: 0.75 }}>{t('Team ({count})', { count: team.length })}</Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {team.map((member) => (
                    <Button key={member.id} size="small" variant="outlined" component={RouterLink} to={`/people/${member.id}`}>
                      {fullName(member)}
                    </Button>
                  ))}
                </Box>
              </>
            )}
          </CardContent>
        </Card>
      </Box>

      {person.role === 'employee' && (
        <Card>
          <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Typography variant="h6" component="h2">{t('Next six weeks')}</Typography>
            <ErrorAlert error={strip.error} onRetry={strip.reload} />
            {strip.data && strip.data.people.length > 0 && (
              <CapacityHeatMap weeks={strip.data.weeks} people={strip.data.people} currentWeek={thisWeek}
                selectedWeek={week} onSelectWeek={setWeek} />
            )}
            <Typography variant="subtitle1">{t('Week of {date}', { date: formatDate(week) })}</Typography>
            <ErrorAlert error={detail.error} onRetry={detail.reload} />
            {detail.data && detail.data.assignments.length === 0 && (
              <Typography color="text.secondary">{t('Nothing booked this week.')}</Typography>
            )}
            {detail.data && detail.data.assignments.map((a) => (
              <Box key={a.assignment_id} sx={{ display: 'flex', justifyContent: 'space-between', gap: 2, borderTop: 1, borderColor: 'divider', pt: 1 }}>
                <Box>
                  <Link component={RouterLink} to={`/projects/${a.project_id}?milestone=${a.milestone_id}`} underline="hover" sx={{ fontWeight: 600 }}>
                    {a.project_name}
                  </Link>
                  <Typography variant="body2" color="text.secondary">{a.milestone_name}</Typography>
                </Box>
                <Typography sx={{ fontWeight: 600 }}>{formatHours(a.hours)}</Typography>
              </Box>
            ))}
            {detail.data && (
              <Typography variant="body2" color="text.secondary">
                {t('{hours} not yet assigned', { hours: formatHours(detail.data.available) })}
                {' · '}
                <Link component="button" type="button" onClick={() => setWeek(addWeeks(week, 1))}>{t('Next week')}</Link>
              </Typography>
            )}
          </CardContent>
        </Card>
      )}

      {dialog === 'assign' && (
        <AssignHoursDialog open employees={[person]} projects={assignable} defaultWeek={week}
          onClose={() => setDialog(null)} onSaved={() => { notify(t('Hours saved')); refresh(); }} />
      )}
      {dialog === 'edit' && (
        <UserDialog open user={person} managers={managerUsers} onClose={() => setDialog(null)}
          onSaved={() => { notify(t('Saved')); refresh(); }} />
      )}
    </Stack>
  );
}
