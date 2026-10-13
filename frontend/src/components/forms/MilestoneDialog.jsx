import { TextField } from '@mui/material';
import { useState } from 'react';
import PropTypes from 'prop-types';
import { api } from '../../api/client.js';
import useSubmit from '../../hooks/useSubmit.js';
import { useT } from '../../i18n/LanguageContext.js';
import { fieldError, formatDate } from '../../utils/format.js';
import FormDialog from './FormDialog.jsx';

function toForm(milestone) {
  return {
    name: milestone?.name || '',
    goal: milestone?.goal || '',
    deliverables: (milestone?.deliverables || []).join('\n'),
    start_date: milestone?.start_date || '',
    end_date: milestone?.end_date || '',
  };
}

// [MILESTONE FORM HERE]
// How: Creates or edits a milestone. Deliverables are typed one per line and
//      sent as a list; when editing, only changed fields are sent.
// Why: One-per-line is the quickest way to enter a short checklist, and the
//      backend checks the dates fit inside the project before saving.
/** Create or edit a milestone. */
export default function MilestoneDialog({ open, project, milestone, onClose, onSaved }) {
  const t = useT();
  const [form, setForm] = useState(() => toForm(milestone));
  const { busy, error, run } = useSubmit();
  const editing = Boolean(milestone);
  const set = (field) => (event) => setForm({ ...form, [field]: event.target.value });

  const submit = async () => {
    const values = {
      name: form.name,
      goal: form.goal,
      deliverables: form.deliverables.split('\n').map((line) => line.trim()).filter(Boolean),
      start_date: form.start_date,
      end_date: form.end_date,
    };
    let body = values;
    if (editing) {
      const original = toForm(milestone);
      body = Object.fromEntries(Object.entries(values).filter(([key, value]) =>
        key === 'deliverables' ? value.join('\n') !== original.deliverables : value !== original[key]));
      if (!Object.keys(body).length) {
        onClose();
        return;
      }
    }
    const ok = await run(async () => {
      const saved = editing
        ? await api(`/milestones/${milestone.id}`, { method: 'PATCH', body })
        : await api(`/projects/${project.id}/milestones`, { method: 'POST', body });
      onSaved(saved);
    });
    if (ok) onClose();
  };

  const err = (field) => t(fieldError(error, field));
  return (
    <FormDialog open={open} title={editing ? t('Edit milestone') : t('New milestone')} onClose={onClose}
      onSubmit={submit} busy={busy} error={error} submitLabel={editing ? 'Save changes' : 'Add milestone'}>
      <TextField label={t('Name')} value={form.name} onChange={set('name')} required error={!!err('name')} helperText={err('name')} />
      <TextField label={t('Goal')} value={form.goal} onChange={set('goal')} multiline minRows={2}
        placeholder={t('e.g. Decommission 200 servers')} error={!!err('goal')} helperText={err('goal')} />
      <TextField label={t('Deliverables (one per line)')} value={form.deliverables} onChange={set('deliverables')}
        multiline minRows={3} error={!!err('deliverables')} helperText={err('deliverables')} />
      <TextField label={t('Start date')} type="date" value={form.start_date} onChange={set('start_date')} required
        slotProps={{ inputLabel: { shrink: true }, htmlInput: { min: project.start_date, max: project.end_date } }}
        error={!!err('start_date')} helperText={err('start_date') || t('Project runs {start} to {end}', { start: formatDate(project.start_date), end: formatDate(project.end_date) })} />
      <TextField label={t('End date')} type="date" value={form.end_date} onChange={set('end_date')} required
        slotProps={{ inputLabel: { shrink: true }, htmlInput: { min: project.start_date, max: project.end_date } }}
        error={!!err('end_date')} helperText={err('end_date')} />
    </FormDialog>
  );
}

MilestoneDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  project: PropTypes.object.isRequired,
  milestone: PropTypes.object,
  onClose: PropTypes.func.isRequired,
  onSaved: PropTypes.func.isRequired,
};
