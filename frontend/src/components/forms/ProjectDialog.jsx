import { InputAdornment, MenuItem, TextField } from '@mui/material';
import PropTypes from 'prop-types';
import { useState } from 'react';
import { api } from '../../api/client.js';
import useSubmit from '../../hooks/useSubmit.js';
import { useT } from '../../i18n/LanguageContext.js';
import { addDays, daysBetween, fieldError, fullName } from '../../utils/format.js';
import FormDialog from './FormDialog.jsx';
import ShiftOptions from './ShiftOptions.jsx';

const EMPTY = { name: '', description: '', start_date: '', end_date: '', allocated_hours: '', budget: '', manager_id: '' };

function toForm(project) {
  if (!project) return EMPTY;
  return {
    name: project.name,
    description: project.description || '',
    start_date: project.start_date,
    end_date: project.end_date,
    allocated_hours: String(project.allocated_hours),
    budget: project.budget ?? '',
    manager_id: project.manager_id,
  };
}

// [ACME: PROJECT FORM HERE]
// How: One form for creating (admins) and editing (the project's manager or
//      an admin). When editing, only the fields that actually changed are
//      sent. The manager picker only appears for admins.
// Why: Sending just the changes keeps the audit log precise ("budget changed
//      from X to Y") instead of recording every field on every save.
/** Create or edit a project. */
export default function ProjectDialog({ open, project, managers = [], milestones = [], canPickManager, onClose, onSaved }) {
  const t = useT();
  const [form, setForm] = useState(() => toForm(project));
  const [shift, setShift] = useState(true);
  const [extend, setExtend] = useState(false);
  const { busy, error, run } = useSubmit();
  const editing = Boolean(project);

  const set = (field) => (event) => setForm({ ...form, [field]: event.target.value });

  const datePattern = /^\d{4}-\d{2}-\d{2}$/;
  const days = project && datePattern.test(form.start_date) ? daysBetween(project.start_date, form.start_date) : 0;
  const moves = days ? milestones
    .filter((m) => m.status === 'active' && !m.is_archived)
    .map((m) => ({ ...m, start: addDays(m.start_date, days), end: addDays(m.end_date, days) })) : [];
  const latestEnd = shift ? moves.map((m) => m.end).sort().pop() : null;
  const overflowEnd = latestEnd && datePattern.test(form.end_date) && latestEnd > form.end_date ? latestEnd : null;

  const submit = async () => {
    const values = {
      name: form.name,
      description: form.description,
      start_date: form.start_date,
      end_date: form.end_date,
      allocated_hours: form.allocated_hours === '' ? undefined : Number(form.allocated_hours),
    };
    // [ACME: BUDGET FIELD HERE]
    // How: The budget field (and its value) is only included for admins;
    //      managers see the budget on the project page but can't edit it.
    // Why: Only admins set budgets, and the backend refuses it from managers.
    if (canPickManager) {
      values.budget = form.budget === '' ? null : Number(form.budget);
      values.manager_id = form.manager_id || undefined;
    }

    let body = values;
    if (editing) {
      const original = toForm(project);
      body = Object.fromEntries(Object.entries(values).filter(([key, value]) => {
        const before = key === 'budget' ? (original.budget === '' ? null : Number(original.budget))
          : key === 'allocated_hours' ? Number(original.allocated_hours) : original[key];
        return value !== undefined && value !== before;
      }));
      if (!Object.keys(body).length) {
        onClose();
        return;
      }
      if (moves.length) body.shift_milestones = shift;
      if (overflowEnd) body.extend_project = extend;
    }
    const ok = await run(async () => {
      const saved = editing
        ? await api(`/projects/${project.id}`, { method: 'PATCH', body })
        : await api('/projects', { method: 'POST', body });
      onSaved(saved);
    });
    if (ok) onClose();
  };

  const err = (field) => t(fieldError(error, field));
  return (
    <FormDialog open={open} title={editing ? t('Edit project') : t('New project')} onClose={onClose}
      onSubmit={submit} busy={busy} error={error} submitLabel={editing ? 'Save changes' : 'Create project'}>
      <TextField label={t('Name')} value={form.name} onChange={set('name')} required error={!!err('name')} helperText={err('name')} />
      <TextField label={t('Description and goal')} value={form.description} onChange={set('description')} multiline minRows={2}
        error={!!err('description')} helperText={err('description')} />
      <TextField label={t('Start date')} type="date" value={form.start_date} onChange={set('start_date')} required
        slotProps={{ inputLabel: { shrink: true } }} error={!!err('start_date')} helperText={err('start_date')} />
      <TextField label={t('End date')} type="date" value={form.end_date} onChange={set('end_date')} required
        slotProps={{ inputLabel: { shrink: true } }} error={!!err('end_date')} helperText={err('end_date')} />
      <TextField label={t('Allocated hours')} type="number" value={form.allocated_hours} onChange={set('allocated_hours')} required
        slotProps={{ htmlInput: { min: 1, step: 1 } }} error={!!err('allocated_hours')}
        helperText={err('allocated_hours') || t('Total hours the project may use across all milestones.')} />
      {canPickManager && (
        <TextField label={t('Budget')} type="number" value={form.budget} onChange={set('budget')}
          slotProps={{ htmlInput: { min: 0, step: 100 }, input: { startAdornment: <InputAdornment position="start">$</InputAdornment> } }}
          error={!!err('budget')} helperText={err('budget') || t('Optional. Compared with labor cost on the dashboard.')} />
      )}
      {editing && (
        <ShiftOptions moves={moves} days={days} shift={shift} onShiftChange={setShift}
          overflowEnd={overflowEnd} extend={extend} onExtendChange={setExtend}
          label="Also move the {count} open milestones {amount}" />
      )}
      {canPickManager && (
        <TextField select label={t('Project manager')} value={form.manager_id} onChange={set('manager_id')} required
          error={!!err('manager_id')} helperText={err('manager_id')}>
          {managers.map((m) => (
            <MenuItem key={m.id} value={m.id}>{fullName(m)} ({t(m.role === 'admin' ? 'Admin' : 'Manager')})</MenuItem>
          ))}
        </TextField>
      )}
    </FormDialog>
  );
}

ProjectDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  project: PropTypes.object,
  managers: PropTypes.arrayOf(PropTypes.object),
  milestones: PropTypes.arrayOf(PropTypes.object),
  canPickManager: PropTypes.bool,
  onClose: PropTypes.func.isRequired,
  onSaved: PropTypes.func.isRequired,
};
