import { Alert, MenuItem, TextField } from '@mui/material';
import PropTypes from 'prop-types';
import { useEffect, useState } from 'react';
import { api } from '../../api/client.js';
import useSubmit from '../../hooks/useSubmit.js';
import { useT } from '../../i18n/LanguageContext.js';
import { fieldError, formatHours, fullName, mondayOf } from '../../utils/format.js';
import FormDialog from './FormDialog.jsx';

// [ACME: ASSIGN HOURS FORM HERE]
// How: The manager picks a project first, then one of its active milestones,
//      then an employee from that project manager's team, a week, and the
//      hours. While they choose, the form shows how many of that person's 40
//      hours are still free that week. Editing only changes the hours.
// Why: Picking the project first means only people who can actually work on
//      it are offered (found in the role-overlap review: admins were offered
//      everyone, and the save then failed). The backend still enforces the
//      40-hour and project limits and explains any refusal.
/** Assign or change an employee's hours on a milestone. */
export default function AssignHoursDialog({ open, employees, projects, assignment, defaultProjectId, defaultWeek, onClose, onSaved }) {
  const t = useT();
  const editing = Boolean(assignment);
  const [form, setForm] = useState({
    user_id: assignment?.user_id || '',
    project_id: assignment?.project_id || defaultProjectId || (projects.length === 1 ? projects[0].id : ''),
    milestone_id: assignment?.milestone_id || '',
    week_start: assignment?.week_start || defaultWeek || mondayOf(),
    hours: assignment ? String(assignment.hours) : '',
  });
  const [milestones, setMilestones] = useState([]);
  const [availability, setAvailability] = useState(null);
  const { busy, error, run } = useSubmit();

  const project = projects.find((p) => p.id === form.project_id);
  const eligible = editing ? employees : employees.filter((e) => project && e.manager_id === project.manager_id);

  useEffect(() => {
    if (!form.project_id || editing) return undefined;
    let current = true;
    api(`/projects/${form.project_id}/milestones`, { query: { status: 'active' } })
      .then((data) => current && setMilestones(data.milestones))
      .catch(() => current && setMilestones([]));
    return () => {
      current = false;
    };
  }, [form.project_id, editing]);

  useEffect(() => {
    if (!form.user_id || !form.week_start) return undefined;
    let current = true;
    api(`/users/${form.user_id}/availability`, { query: { week: form.week_start } })
      .then((data) => current && setAvailability(data))
      .catch(() => current && setAvailability(null));
    return () => {
      current = false;
    };
  }, [form.user_id, form.week_start]);

  const set = (field) => (event) => {
    const next = { ...form, [field]: event.target.value };
    if (field === 'project_id') {
      next.milestone_id = '';
      next.user_id = '';
    }
    setForm(next);
  };

  const submit = async () => {
    const ok = await run(async () => {
      const saved = editing
        ? await api(`/hour-assignments/${assignment.id}`, { method: 'PATCH', body: { hours: Number(form.hours) } })
        : await api('/hour-assignments', {
          method: 'POST',
          body: {
            user_id: form.user_id,
            milestone_id: form.milestone_id,
            week_start: form.week_start,
            hours: form.hours === '' ? undefined : Number(form.hours),
          },
        });
      onSaved(saved);
    });
    if (ok) onClose();
  };

  const free = availability ? Number(availability.available) + (editing ? Number(assignment.hours) : 0) : null;
  const person = employees.find((p) => p.id === form.user_id);
  const err = (field) => t(fieldError(error, field));
  return (
    <FormDialog open={open} title={editing ? t('Change hours') : t('Assign hours')} onClose={onClose}
      onSubmit={submit} busy={busy} error={error} submitLabel={editing ? 'Save' : 'Assign'}>
      {!editing && (
        <>
          <TextField select label={t('Project')} value={form.project_id} onChange={set('project_id')} required>
            {projects.map((p) => <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>)}
          </TextField>
          <TextField select label={t('Milestone')} value={form.milestone_id} onChange={set('milestone_id')} required
            disabled={!form.project_id} error={!!err('milestone_id')}
            helperText={err('milestone_id') || (form.project_id && !milestones.length ? t('This project has no active milestones.') : '')}>
            {milestones.map((m) => <MenuItem key={m.id} value={m.id}>{m.sequence}. {m.name}</MenuItem>)}
          </TextField>
        </>
      )}
      <TextField select label={t('Employee')} value={form.user_id} onChange={set('user_id')} required
        disabled={editing || !form.project_id} error={!!err('user_id')}
        helperText={err('user_id') || (!editing && project && !eligible.length ? t("This project manager's team has no employees.") : '')}>
        {eligible.map((p) => <MenuItem key={p.id} value={p.id}>{fullName(p)}</MenuItem>)}
      </TextField>
      {!editing && (
        <TextField label={t('Week (any day in the week)')} type="date" value={form.week_start} onChange={set('week_start')} required
          slotProps={{ inputLabel: { shrink: true } }} error={!!err('week_start')} helperText={err('week_start')} />
      )}
      {free !== null && person && (
        <Alert severity={free > 0 ? 'info' : 'warning'}>
          {t('{name} has {hours} of 40 h free that week.', { name: fullName(person), hours: formatHours(free) })}
        </Alert>
      )}
      <TextField label={t('Hours')} type="number" value={form.hours} onChange={set('hours')} required
        slotProps={{ htmlInput: { min: 0.5, max: 40, step: 0.5 } }} error={!!err('hours')} helperText={err('hours')} />
    </FormDialog>
  );
}

AssignHoursDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  employees: PropTypes.arrayOf(PropTypes.object).isRequired,
  projects: PropTypes.arrayOf(PropTypes.object).isRequired,
  assignment: PropTypes.object,
  defaultProjectId: PropTypes.string,
  defaultWeek: PropTypes.string,
  onClose: PropTypes.func.isRequired,
  onSaved: PropTypes.func.isRequired,
};
