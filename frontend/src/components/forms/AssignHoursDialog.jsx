import { Alert, MenuItem, TextField } from '@mui/material';
import { useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import { api } from '../../api/client.js';
import useSubmit from '../../hooks/useSubmit.js';
import { fieldError, formatHours, fullName, mondayOf } from '../../utils/format.js';
import FormDialog from './FormDialog.jsx';

// [ASSIGN HOURS FORM HERE]
// How: The manager picks an employee, a project and one of its active
//      milestones, a week, and the hours. While they choose, the form shows
//      how many of that person's 40 hours are still free that week. Editing
//      an existing assignment only changes the hours.
// Why: Seeing the free hours up front avoids guesswork; the backend still
//      enforces the 40-hour and project limits and explains any refusal.
/** Assign or change an employee's hours on a milestone. */
export default function AssignHoursDialog({ open, employees, projects, assignment, defaultProjectId, defaultWeek, onClose, onSaved }) {
  const editing = Boolean(assignment);
  const [form, setForm] = useState({
    user_id: assignment?.user_id || '',
    project_id: assignment?.project_id || defaultProjectId || '',
    milestone_id: assignment?.milestone_id || '',
    week_start: assignment?.week_start || defaultWeek || mondayOf(),
    hours: assignment ? String(assignment.hours) : '',
  });
  const [milestones, setMilestones] = useState([]);
  const [availability, setAvailability] = useState(null);
  const { busy, error, run } = useSubmit();

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
    if (field === 'project_id') next.milestone_id = '';
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
  const err = (field) => fieldError(error, field);
  return (
    <FormDialog open={open} title={editing ? 'Change hours' : 'Assign hours'} onClose={onClose}
      onSubmit={submit} busy={busy} error={error} submitLabel={editing ? 'Save' : 'Assign'}>
      <TextField select label="Employee" value={form.user_id} onChange={set('user_id')} required disabled={editing}
        error={!!err('user_id')} helperText={err('user_id')}>
        {employees.map((person) => <MenuItem key={person.id} value={person.id}>{fullName(person)}</MenuItem>)}
      </TextField>
      {!editing && (
        <>
          <TextField select label="Project" value={form.project_id} onChange={set('project_id')} required>
            {projects.map((project) => <MenuItem key={project.id} value={project.id}>{project.name}</MenuItem>)}
          </TextField>
          <TextField select label="Milestone" value={form.milestone_id} onChange={set('milestone_id')} required
            disabled={!form.project_id} error={!!err('milestone_id')}
            helperText={err('milestone_id') || (form.project_id && !milestones.length ? 'This project has no active milestones.' : '')}>
            {milestones.map((m) => <MenuItem key={m.id} value={m.id}>{m.sequence}. {m.name}</MenuItem>)}
          </TextField>
          <TextField label="Week (any day in the week)" type="date" value={form.week_start} onChange={set('week_start')} required
            slotProps={{ inputLabel: { shrink: true } }} error={!!err('week_start')} helperText={err('week_start')} />
        </>
      )}
      {free !== null && (
        <Alert severity={free > 0 ? 'info' : 'warning'}>
          {fullName(employees.find((p) => p.id === form.user_id))} has {formatHours(free)} of 40 h free that week.
        </Alert>
      )}
      <TextField label="Hours" type="number" value={form.hours} onChange={set('hours')} required
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
