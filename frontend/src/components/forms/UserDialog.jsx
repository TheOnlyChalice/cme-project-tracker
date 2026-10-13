import { InputAdornment, MenuItem, TextField } from '@mui/material';
import { useState } from 'react';
import PropTypes from 'prop-types';
import { api } from '../../api/client.js';
import useSubmit from '../../hooks/useSubmit.js';
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
      manager_id: form.manager_id || null,
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

  const err = (field) => fieldError(error, field);
  const managerOptions = managers.filter((m) => m.id !== user?.id);
  return (
    <FormDialog open={open} title={editing ? `Edit ${fullName(user)}` : 'New person'} onClose={onClose}
      onSubmit={submit} busy={busy} error={error} submitLabel={editing ? 'Save changes' : 'Create'}>
      <TextField label="First name" value={form.first_name} onChange={set('first_name')} required error={!!err('first_name')} helperText={err('first_name')} />
      <TextField label="Last name" value={form.last_name} onChange={set('last_name')} required error={!!err('last_name')} helperText={err('last_name')} />
      <TextField label="Email" type="email" value={form.email} onChange={set('email')} required error={!!err('email')} helperText={err('email')} />
      <TextField select label="Role" value={form.role} onChange={set('role')} required error={!!err('role')} helperText={err('role')}>
        <MenuItem value="employee">Employee</MenuItem>
        <MenuItem value="manager">Manager</MenuItem>
        <MenuItem value="admin">Admin</MenuItem>
      </TextField>
      <TextField select label="Reports to" value={form.manager_id} onChange={set('manager_id')}
        required={form.role === 'employee'} error={!!err('manager_id')}
        helperText={err('manager_id') || (form.role === 'employee' ? 'Employees must have a manager.' : 'Optional for managers and admins.')}>
        <MenuItem value="">No manager</MenuItem>
        {managerOptions.map((m) => <MenuItem key={m.id} value={m.id}>{fullName(m)} ({m.role})</MenuItem>)}
      </TextField>
      <TextField label="Job title" value={form.job_title} onChange={set('job_title')} error={!!err('job_title')} helperText={err('job_title')} />
      <TextField label="Annual salary" type="number" value={form.salary} onChange={set('salary')}
        slotProps={{ htmlInput: { min: 0, step: 1000 }, input: { startAdornment: <InputAdornment position="start">$</InputAdornment> } }}
        error={!!err('salary')} helperText={err('salary') || 'Only admins can see this. Used for project labor cost.'} />
      <TextField label={editing ? 'New password (leave blank to keep)' : 'Temporary password'} type="password"
        value={form.password} onChange={set('password')} required={!editing} autoComplete="new-password"
        error={!!err('password')} helperText={err('password') || 'At least 8 characters with a letter and a number.'} />
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
