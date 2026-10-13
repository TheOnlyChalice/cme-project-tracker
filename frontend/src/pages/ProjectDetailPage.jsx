import AddIcon from '@mui/icons-material/Add';
import ArchiveIcon from '@mui/icons-material/Archive';
import BlockIcon from '@mui/icons-material/Block';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import EditIcon from '@mui/icons-material/Edit';
import UnarchiveIcon from '@mui/icons-material/Unarchive';
import {
  Box, Button, Card, CardContent, Chip, Divider, IconButton, List, ListItem, ListItemText,
  Paper, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Tooltip, Typography,
} from '@mui/material';
import { useState } from 'react';
import { Link as RouterLink, useNavigate, useParams } from 'react-router-dom';
import { api } from '../api/client.js';
import { useAuth } from '../auth/AuthContext.js';
import ConfirmDialog from '../components/ConfirmDialog.jsx';
import ErrorAlert from '../components/ErrorAlert.jsx';
import AssignHoursDialog from '../components/forms/AssignHoursDialog.jsx';
import MilestoneDialog from '../components/forms/MilestoneDialog.jsx';
import ProjectDialog from '../components/forms/ProjectDialog.jsx';
import Loading from '../components/Loading.jsx';
import { useNotify } from '../components/NotifyContext.js';
import PageHeader from '../components/PageHeader.jsx';
import ProgressCell from '../components/ProgressCell.jsx';
import RiskFlags from '../components/RiskFlags.jsx';
import StatCard from '../components/StatCard.jsx';
import StatusChip from '../components/StatusChip.jsx';
import WeekPicker from '../components/WeekPicker.jsx';
import useLoader from '../hooks/useLoader.js';
import { formatDate, formatHours, formatMoney, fullName, mondayOf } from '../utils/format.js';
import { canManageProject, isAdmin } from '../utils/roles.js';

// [PROJECT DETAIL HERE]
// How: One page per project with its health numbers, the milestone chain,
//      and the hours booked for a chosen week. Buttons only appear when the
//      signed-in user is allowed to use them (manager of this project or an
//      admin; abandon, archive, and restore are admin-only).
// Why: Everything a manager needs to run a project is in one place, and the
//      confirmation dialogs guard actions that close or archive a project.
/** One project: health, milestones, and booked hours. */
export default function ProjectDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const notify = useNotify();
  const navigate = useNavigate();
  const admin = isAdmin(user);
  const [week, setWeek] = useState(mondayOf());
  const [dialog, setDialog] = useState(null);

  const main = useLoader(async () => {
    const [project, health, milestones, chain, users] = await Promise.all([
      api(`/projects/${id}`),
      api(`/projects/${id}/health`),
      api(`/projects/${id}/milestones`, { query: { include_archived: admin ? 'true' : '' } }),
      api(`/projects/${id}/milestone-chain`),
      api('/users'),
    ]);
    return { project, health, milestones: milestones.milestones, chain: chain.milestones, users: users.users };
  }, [id, admin]);

  const hours = useLoader(
    () => api('/hour-assignments', { query: { project_id: id, week } }).then((d) => d.assignments),
    [id, week],
  );

  if (main.loading && !main.data) return <Loading label="Loading project" />;
  if (main.error) {
    return main.error.status === 404 ? (
      <Box sx={{ py: 6, textAlign: 'center' }}>
        <Typography variant="h6">Project not found</Typography>
        <Typography color="text.secondary" sx={{ mb: 2 }}>It may be completed, archived, or outside your access.</Typography>
        <Button component={RouterLink} to="/projects">Back to projects</Button>
      </Box>
    ) : <ErrorAlert error={main.error} onRetry={main.reload} />;
  }

  const { project, health, milestones, chain, users } = main.data;
  const people = Object.fromEntries(users.map((u) => [u.id, u]));
  const chainById = Object.fromEntries(chain.map((c) => [c.id, c]));
  const open = project.status === 'active' && !project.is_archived;
  const canManage = canManageProject(user, project) && open;
  const team = users.filter((u) => u.role === 'employee' && u.manager_id === project.manager_id && !u.is_archived);
  const refresh = () => {
    main.reload();
    hours.reload();
  };
  const close = () => setDialog(null);

  const action = (path, message) => async () => {
    await api(path, { method: 'POST' });
    notify(message);
    refresh();
  };

  // [LEAVE CLOSED PROJECT HERE]
  // How: After a manager completes their project, they're taken back to the
  //      project list; admins stay on the page.
  // Why: Completed projects are archived and only admins can see archived
  //      work, so a manager staying here would immediately get "not found".
  const completeProject = async () => {
    await api(`/projects/${id}/complete`, { method: 'POST' });
    notify('Project completed');
    if (admin) refresh();
    else navigate('/projects');
  };

  return (
    <>
      <PageHeader
        title={project.name}
        subtitle={`Managed by ${people[project.manager_id] ? fullName(people[project.manager_id]) : 'another manager'} · ${formatDate(project.start_date)} – ${formatDate(project.end_date)}`}
        actions={(
          <>
            {canManage && <Button startIcon={<EditIcon />} onClick={() => setDialog({ type: 'edit' })}>Edit</Button>}
            {canManage && <Button startIcon={<CheckCircleIcon />} color="success" onClick={() => setDialog({ type: 'complete' })}>Complete</Button>}
            {admin && open && <Button startIcon={<BlockIcon />} color="warning" onClick={() => setDialog({ type: 'abandon' })}>Abandon</Button>}
            {admin && !project.is_archived && <Button startIcon={<ArchiveIcon />} color="error" onClick={() => setDialog({ type: 'archive' })}>Archive</Button>}
            {admin && project.is_archived && <Button startIcon={<UnarchiveIcon />} variant="contained" onClick={() => setDialog({ type: 'restore' })}>Restore</Button>}
          </>
        )}
      />

      <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
        <StatusChip value={project.status} />
        {project.is_archived && <StatusChip archived />}
        <RiskFlags flags={health.risk_flags} />
      </Stack>
      {project.description && <Typography sx={{ mb: 3, maxWidth: 800 }}>{project.description}</Typography>}

      <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', lg: 'repeat(4, 1fr)' }, mb: 3 }}>
        <StatCard label="Milestones complete" value={`${health.milestones_completed} / ${health.milestones_total}`}
          caption={`${Math.round(health.percent_time_elapsed)}% of the time has passed`} />
        <StatCard label="Days left" value={health.days_left} color={health.days_left < 0 ? 'error.main' : undefined}
          caption={`Ends ${formatDate(project.end_date)}`} />
        <Card><CardContent>
          <Typography variant="body2" color="text.secondary" gutterBottom>Hours assigned</Typography>
          <ProgressCell value={health.percent_hours_assigned} label={`${formatHours(health.hours_assigned)} of ${health.allocated_hours} h`} />
        </CardContent></Card>
        {'budget' in health ? (
          <Card><CardContent>
            <Typography variant="body2" color="text.secondary" gutterBottom>Budget used to date</Typography>
            <ProgressCell value={health.percent_budget_used}
              label={health.budget ? `${formatMoney(health.labor_cost_to_date)} of ${formatMoney(health.budget)}` : 'No budget set'} />
            <Typography variant="caption" color="text.secondary">Forecast: {formatMoney(health.labor_cost_committed)}</Typography>
          </CardContent></Card>
        ) : <StatCard label="Status" value={project.status === 'active' ? 'Active' : project.status} />}
      </Box>

      {/* [MILESTONE CHAIN VIEW HERE]
          How: Milestones are listed in sequence order, each marked blocked
               (an earlier milestone is still open) or overdue, with its goal,
               deliverables, and who has hours on it.
          Why: This is the dependency chain from the business questions:
               managers can see which step is holding up the rest. */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
        <Typography variant="h6" component="h2" sx={{ flexGrow: 1 }}>Milestones</Typography>
        {canManage && <Button startIcon={<AddIcon />} onClick={() => setDialog({ type: 'milestone' })}>Add milestone</Button>}
      </Box>
      {milestones.length === 0 && <Typography color="text.secondary" sx={{ mb: 3 }}>No milestones yet.</Typography>}
      <Stack spacing={2} sx={{ mb: 4 }}>
        {milestones.map((m) => {
          const link = chainById[m.id] || {};
          const editable = canManage && m.status === 'active' && !m.is_archived;
          return (
            <Card key={m.id} sx={{ opacity: m.is_archived ? 0.6 : 1, borderColor: link.overdue ? 'warning.main' : undefined }}>
              <CardContent>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 1 }}>
                  <Typography variant="subtitle1" fontWeight={600} sx={{ flexGrow: 1 }}>
                    {m.sequence}. {m.name}
                  </Typography>
                  {project.active_milestone_id === m.id && <Chip size="small" color="primary" variant="outlined" label="Current" />}
                  <StatusChip value={m.status} archived={m.is_archived} />
                  {link.blocked && <Tooltip title="An earlier milestone is still open"><Chip size="small" label="Blocked" /></Tooltip>}
                  {link.overdue && <Chip size="small" color="warning" label="Overdue" />}
                  {editable && (
                    <>
                      <Tooltip title="Edit"><IconButton size="small" aria-label={`Edit ${m.name}`} onClick={() => setDialog({ type: 'milestone', milestone: m })}><EditIcon fontSize="small" /></IconButton></Tooltip>
                      <Tooltip title="Mark complete"><IconButton size="small" color="success" aria-label={`Complete ${m.name}`} onClick={() => setDialog({ type: 'completeMilestone', milestone: m })}><CheckCircleIcon fontSize="small" /></IconButton></Tooltip>
                      <Tooltip title="Archive"><IconButton size="small" aria-label={`Archive ${m.name}`} onClick={() => setDialog({ type: 'archiveMilestone', milestone: m })}><ArchiveIcon fontSize="small" /></IconButton></Tooltip>
                    </>
                  )}
                  {admin && m.is_archived && open && (
                    <Button size="small" startIcon={<UnarchiveIcon />} onClick={() => setDialog({ type: 'restoreMilestone', milestone: m })}>Restore</Button>
                  )}
                </Box>
                <Typography variant="body2" color="text.secondary">
                  {formatDate(m.start_date)} – {formatDate(m.end_date)} · {m.assigned_employee_ids.length} people with hours
                </Typography>
                {m.goal && <Typography sx={{ mt: 1 }}><strong>Goal:</strong> {m.goal}</Typography>}
                {m.deliverables.length > 0 && (
                  <List dense disablePadding sx={{ mt: 0.5 }}>
                    {m.deliverables.map((d) => (
                      <ListItem key={d} disableGutters sx={{ py: 0 }}><ListItemText primary={`• ${d}`} /></ListItem>
                    ))}
                  </List>
                )}
              </CardContent>
            </Card>
          );
        })}
      </Stack>

      <Divider sx={{ mb: 3 }} />
      <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 2, mb: 1 }}>
        <Typography variant="h6" component="h2" sx={{ flexGrow: 1 }}>Hours booked</Typography>
        <WeekPicker week={week} onChange={setWeek} />
        {canManage && <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialog({ type: 'assign' })}>Assign hours</Button>}
      </Box>
      <ErrorAlert error={hours.error} onRetry={hours.reload} />
      {hours.data && hours.data.length === 0 && <Typography color="text.secondary">No hours booked on this project that week.</Typography>}
      {hours.data && hours.data.length > 0 && (
        <TableContainer component={Paper} variant="outlined">
          <Table size="small" aria-label="Hours booked">
            <TableHead>
              <TableRow>
                <TableCell>Person</TableCell>
                <TableCell>Milestone</TableCell>
                <TableCell align="right">Hours</TableCell>
                {canManage && <TableCell align="right">Actions</TableCell>}
              </TableRow>
            </TableHead>
            <TableBody>
              {hours.data.map((a) => (
                <TableRow key={a.id}>
                  <TableCell>{people[a.user_id] ? fullName(people[a.user_id]) : 'Teammate'}</TableCell>
                  <TableCell>{milestones.find((m) => m.id === a.milestone_id)?.name || '—'}</TableCell>
                  <TableCell align="right">{formatHours(a.hours)}</TableCell>
                  {canManage && (
                    <TableCell align="right">
                      <IconButton size="small" aria-label="Change hours" onClick={() => setDialog({ type: 'assign', assignment: a })}><EditIcon fontSize="small" /></IconButton>
                      <IconButton size="small" aria-label="Remove hours" onClick={() => setDialog({ type: 'removeHours', assignment: a })}><DeleteOutlineIcon fontSize="small" /></IconButton>
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {dialog?.type === 'edit' && (
        <ProjectDialog open project={project} canPickManager={admin}
          managers={users.filter((u) => u.role !== 'employee' && !u.is_archived)}
          onClose={close} onSaved={() => { notify('Project saved'); refresh(); }} />
      )}
      {dialog?.type === 'milestone' && (
        <MilestoneDialog open project={project} milestone={dialog.milestone} onClose={close}
          onSaved={() => { notify('Milestone saved'); refresh(); }} />
      )}
      {dialog?.type === 'assign' && (
        <AssignHoursDialog open employees={team} projects={[project]} assignment={dialog.assignment}
          defaultProjectId={project.id} defaultWeek={week} onClose={close}
          onSaved={() => { notify('Hours saved'); refresh(); }} />
      )}
      <ConfirmDialog open={dialog?.type === 'complete'} title="Complete this project?" confirmLabel="Complete" color="success"
        message="The project will be marked completed and archived. Future booked hours are released. Only an admin can reopen it."
        onConfirm={completeProject} onClose={close} />
      <ConfirmDialog open={dialog?.type === 'abandon'} title="Abandon this project?" confirmLabel="Abandon" color="warning"
        message="The project will be marked abandoned and archived. Future booked hours are released."
        onConfirm={action(`/projects/${id}/abandon`, 'Project abandoned')} onClose={close} />
      <ConfirmDialog open={dialog?.type === 'archive'} title="Archive this project?" confirmLabel="Archive" color="error"
        message="Archived projects are hidden from everyone except admins. You can restore it later."
        onConfirm={async () => { await api(`/projects/${id}`, { method: 'DELETE' }); notify('Project archived'); refresh(); }} onClose={close} />
      <ConfirmDialog open={dialog?.type === 'restore'} title="Restore this project?" confirmLabel="Restore"
        message="The project becomes active again and visible to its manager and team."
        onConfirm={action(`/projects/${id}/restore`, 'Project restored')} onClose={close} />
      <ConfirmDialog open={dialog?.type === 'completeMilestone'} title={`Complete "${dialog?.milestone?.name}"?`} confirmLabel="Complete" color="success"
        message="The milestone is marked completed, the next one becomes current, and future booked hours on it are released."
        onConfirm={action(`/milestones/${dialog?.milestone?.id}/complete`, 'Milestone completed')} onClose={close} />
      <ConfirmDialog open={dialog?.type === 'archiveMilestone'} title={`Archive "${dialog?.milestone?.name}"?`} confirmLabel="Archive" color="error"
        message="The milestone is hidden and its future booked hours are released. An admin can restore it."
        onConfirm={async () => { await api(`/milestones/${dialog.milestone.id}`, { method: 'DELETE' }); notify('Milestone archived'); refresh(); }} onClose={close} />
      <ConfirmDialog open={dialog?.type === 'restoreMilestone'} title={`Restore "${dialog?.milestone?.name}"?`} confirmLabel="Restore"
        message="The milestone becomes visible again."
        onConfirm={action(`/milestones/${dialog?.milestone?.id}/restore`, 'Milestone restored')} onClose={close} />
      <ConfirmDialog open={dialog?.type === 'removeHours'} title="Remove these hours?" confirmLabel="Remove" color="error"
        message="The hours are freed up so they can be booked elsewhere."
        onConfirm={async () => { await api(`/hour-assignments/${dialog.assignment.id}`, { method: 'DELETE' }); notify('Hours removed'); refresh(); }} onClose={close} />
    </>
  );
}
