import { Alert, Box, Button, Card, CardContent, Stack, TextField, Typography } from '@mui/material';
import { useState } from 'react';
import { api } from '../api/client.js';
import { useAuth } from '../auth/AuthContext.js';
import ErrorAlert from '../components/ErrorAlert.jsx';
import { useNotify } from '../components/NotifyContext.js';
import PageHeader from '../components/PageHeader.jsx';
import StatusChip from '../components/StatusChip.jsx';
import useSubmit from '../hooks/useSubmit.js';
import { fieldError } from '../utils/format.js';

// [PROFILE PAGE HERE]
// How: Everyone can update their own name, email, and photo link, and change
//      their password by entering the current one. Changing the password
//      signs out every session, so the page signs straight back in with the
//      new password.
// Why: The requirements let people edit only their own personal data. The
//      automatic re-sign-in keeps this device working while still cutting
//      off any other device that had the old password.
/** The signed-in user's own details and password. */
export default function ProfilePage() {
  const { user, refreshUser, login } = useAuth();
  const notify = useNotify();
  const [details, setDetails] = useState({
    first_name: user.first_name, last_name: user.last_name, email: user.email,
    profile_picture_url: user.profile_picture_url || '',
  });
  const [passwords, setPasswords] = useState({ current_password: '', password: '', confirm: '' });
  const [mismatch, setMismatch] = useState('');
  const save = useSubmit();
  const change = useSubmit();

  const saveDetails = async (event) => {
    event.preventDefault();
    const body = Object.fromEntries(Object.entries(details).filter(([key, value]) => value !== (user[key] || '')));
    if (!Object.keys(body).length) return;
    const ok = await save.run(async () => {
      await api(`/users/${user.id}`, { method: 'PATCH', body });
      await refreshUser();
    });
    if (ok) notify('Profile saved');
  };

  const changePassword = async (event) => {
    event.preventDefault();
    if (passwords.password !== passwords.confirm) {
      setMismatch("The new passwords don't match.");
      return;
    }
    setMismatch('');
    const ok = await change.run(async () => {
      await api(`/users/${user.id}`, {
        method: 'PATCH',
        body: { password: passwords.password, current_password: passwords.current_password },
      });
      await login(user.username, passwords.password);
    });
    if (ok) {
      setPasswords({ current_password: '', password: '', confirm: '' });
      notify('Password changed. Other devices have been signed out.');
    }
  };

  const setD = (field) => (e) => setDetails({ ...details, [field]: e.target.value });
  const setP = (field) => (e) => setPasswords({ ...passwords, [field]: e.target.value });

  return (
    <>
      <PageHeader title="My profile" subtitle={`Signed in as ${user.username}`} actions={<StatusChip value={user.role} />} />
      <Box sx={{ display: 'grid', gap: 3, gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, alignItems: 'start' }}>
        <Card>
          <CardContent component="form" onSubmit={saveDetails} noValidate>
            <Typography variant="h6" component="h2" gutterBottom>Your details</Typography>
            <Stack spacing={2}>
              <ErrorAlert error={save.error && !Object.keys(save.error.details).length ? save.error : null} />
              <TextField label="First name" value={details.first_name} onChange={setD('first_name')} error={!!fieldError(save.error, 'first_name')} helperText={fieldError(save.error, 'first_name')} />
              <TextField label="Last name" value={details.last_name} onChange={setD('last_name')} error={!!fieldError(save.error, 'last_name')} helperText={fieldError(save.error, 'last_name')} />
              <TextField label="Email" type="email" value={details.email} onChange={setD('email')} error={!!fieldError(save.error, 'email')} helperText={fieldError(save.error, 'email')} />
              <TextField label="Profile picture URL" value={details.profile_picture_url} onChange={setD('profile_picture_url')} error={!!fieldError(save.error, 'profile_picture_url')} helperText={fieldError(save.error, 'profile_picture_url') || 'Optional link to an image.'} />
              <Typography variant="body2" color="text.secondary">
                Job title, role, manager, and salary are managed by an admin.
              </Typography>
              <Box><Button type="submit" variant="contained" disabled={save.busy}>{save.busy ? 'Saving…' : 'Save details'}</Button></Box>
            </Stack>
          </CardContent>
        </Card>

        <Card>
          <CardContent component="form" onSubmit={changePassword} noValidate>
            <Typography variant="h6" component="h2" gutterBottom>Change password</Typography>
            <Stack spacing={2}>
              {mismatch && <Alert severity="error">{mismatch}</Alert>}
              <ErrorAlert error={change.error && !Object.keys(change.error.details).length ? change.error : null} />
              <TextField label="Current password" type="password" autoComplete="current-password" value={passwords.current_password} onChange={setP('current_password')}
                error={!!fieldError(change.error, 'current_password')} helperText={fieldError(change.error, 'current_password')} />
              <TextField label="New password" type="password" autoComplete="new-password" value={passwords.password} onChange={setP('password')}
                error={!!fieldError(change.error, 'password')} helperText={fieldError(change.error, 'password') || 'At least 8 characters with a letter and a number.'} />
              <TextField label="Confirm new password" type="password" autoComplete="new-password" value={passwords.confirm} onChange={setP('confirm')} />
              <Box><Button type="submit" variant="contained" disabled={change.busy}>{change.busy ? 'Changing…' : 'Change password'}</Button></Box>
            </Stack>
          </CardContent>
        </Card>
      </Box>
    </>
  );
}
