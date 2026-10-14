import { Alert, InputAdornment, MenuItem, TextField } from '@mui/material';
import { useState } from 'react';
import PropTypes from 'prop-types';
import { api } from '../../api/client.js';
import { useAuth } from '../../auth/AuthContext.js';
import useSubmit from '../../hooks/useSubmit.js';
import { useT } from '../../i18n/LanguageContext.js';
import { fieldError, fullName } from '../../utils/format.js';
import FormDialog from './FormDialog.jsx';

function toForm(user) {
  return {
    first_name: user?.first_name || '',
    last_name: user?.last_name || '',
    email: user?.email || '',
    role: user?.role || 'employee',
    manager_id: user?.manager_id || '',
    job_title: user?.job_title || '',
    salary: user?.salary ?? '',
    password: '',
  };
}

// [USER FORM HERE]
// How: Admins create people (the system generates the 6-character username)
//      and edit their role, manager, job title, and salary. Leaving the
//      password blank when editing keeps the current one.
// Why: Matches the rules that only admins create users and assign roles.
//      Changing someone's role or password signs them out everywhere, which
//      the backend handles automatically.
/** Create or edit a person (admins only). */
export default function UserDialog({ open, user, managers, onClose, onSaved }) {
  const t = useT();
  const { user: me } = useAuth();
  const [form, setForm] = useState(() => toForm(user));
  const { busy, error, run } = useSubmit();
  const editing = Boolean(user);
  const set = (field) => (event) => setForm({ ...form, [field]: event.target.value });

  const submit = async () => {
    const values = {
      first_name: form.first_name,
      last_name: form.last_name,
      email: form.email,
      role: form.role,
      // Only employees have a manager; switching someone to manager or admin
      // clears it (the backend enforces the same rule).
      manager_id: form.role === 'employee' ? form.manager_id || null : null,
      job_title: form.job_title,
      salary: form.salary === '' ? null : Number(form.salary),
    };
    let body = values;
    if (editing) {
      const original = toForm(user);
      body = Object.fromEntries(Object.entries(values).filter(([key, value]) => {
        const before = key === 'manager_id' ? original.manager_id || null
          : key === 'salary' ? (original.salary === '' ? null : Number(original.salary)) : original[key];
        return value !== before;
      }));
      if (form.password) body.password = form.password;
      if (!Object.keys(body).length) {
        onClose();
        return;
      }
    } else {
      body.password = form.password;
      if (!body.manager_id) delete body.manager_id;
    }
    const ok = await run(async () => {
      const saved = editing
        ? await api(`/users/${user.id}`, { method: 'PATCH', body })
        : await api('/users', { method: 'POST', body });
      onSaved(saved);
    });
    if (ok) onClose();
  };

  const err = (field) => t(fieldError(error, field));
  const managerOptions = managers.filter((m) => m.id !== user?.id);
  return (
    <FormDialog open={open} title={editing ? t('Edit {name}', { name: fullName(user) }) : t('New person')} onClose={onClose}
      onSubmit={submit} busy={busy} error={error} submitLabel={editing ? 'Save changes' : 'Create'}>
      {editing && user.id === me?.id && form.role !== user.role && (
        <Alert severity="warning">{t("Changing your own role will sign you out. You'll need to sign in again.")}</Alert>
      )}
      <TextField label={t('First name')} value={form.first_name} onChange={set('first_name')} required error={!!err('first_name')} helperText={err('first_name')} />
      <TextField label={t('Last name')} value={form.last_name} onChange={set('last_name')} required error={!!err('last_name')} helperText={err('last_name')} />
      <TextField label={t('Email')} type="email" value={form.email} onChange={set('email')} required error={!!err('email')} helperText={err('email')} />
      <TextField select label={t('Role')} value={form.role} onChange={set('role')} required error={!!err('role')} helperText={err('role')}>
        <MenuItem value="employee">{t('Employee')}</MenuItem>
        <MenuItem value="manager">{t('Manager')}</MenuItem>
        <MenuItem value="admin">{t('Admin')}</MenuItem>
      </TextField>
      {/* [REPORTS TO FIELD HERE]
          How: The "Reports to" picker only appears for employees, and is required
               for them. Choosing Manager or Admin hides it and clears it.
          Why: Managers and admins lead teams; they don't work under anyone. */}
      {form.role === 'employee' && (
        <TextField select label={t('Reports to')} value={form.manager_id} onChange={set('manager_id')}
          required error={!!err('manager_id')} helperText={err('manager_id') || t('Employees must have a manager.')}>
          {managerOptions.map((m) => <MenuItem key={m.id} value={m.id}>{fullName(m)} ({t(m.role === 'admin' ? 'Admin' : 'Manager')})</MenuItem>)}
        </TextField>
      )}
      <TextField label={t('Job title')} value={form.job_title} onChange={set('job_title')} error={!!err('job_title')} helperText={err('job_title')} />
      <TextField label={t('Annual salary')} type="number" value={form.salary} onChange={set('salary')}
        slotProps={{ htmlInput: { min: 0, step: 1000 }, input: { startAdornment: <InputAdornment position="start">$</InputAdornment> } }}
        error={!!err('salary')} helperText={err('salary') || t('Only admins can see this. Used for project labor cost.')} />
      <TextField label={editing ? t('New password (leave blank to keep)') : t('Temporary password')} type="password"
        value={form.password} onChange={set('password')} required={!editing} autoComplete="new-password"
        error={!!err('password')} helperText={err('password') || t('At least 8 characters with a letter and a number.')} />
    </FormDialog>
  );
}

UserDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  user: PropTypes.object,
  managers: PropTypes.arrayOf(PropTypes.object).isRequired,
  onClose: PropTypes.func.isRequired,
  onSaved: PropTypes.func.isRequired,
};
