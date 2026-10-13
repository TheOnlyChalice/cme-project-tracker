import { Alert, Box, Card, CardContent, Stack, TextField, Typography } from '@mui/material';
import PropTypes from 'prop-types';
import { useState } from 'react';
import { api } from '../api/client.js';
import { useAuth } from '../auth/AuthContext.js';
import BusyButton from '../components/BusyButton.jsx';
import ErrorAlert from '../components/ErrorAlert.jsx';
import { useNotify } from '../components/NotifyContext.js';
import PageHeader from '../components/PageHeader.jsx';
import StatusChip from '../components/StatusChip.jsx';
import useSubmit from '../hooks/useSubmit.js';
import { useT } from '../i18n/LanguageContext.js';
import { fieldError, formatDate } from '../utils/format.js';

/** One read-only label/value row in the account details card. */
function DetailRow({ label, children }) {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2, py: 1 }}>
      <Typography color="text.secondary">{label}</Typography>
      <Box sx={{ textAlign: 'right', fontWeight: 600 }}>{children}</Box>
    </Box>
  );
}

DetailRow.propTypes = {
  label: PropTypes.node.isRequired,
  children: PropTypes.node,
};

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
  const t = useT();
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
    if (ok) notify(t('Profile saved'));
  };

  const changePassword = async (event) => {
    event.preventDefault();
    if (passwords.password !== passwords.confirm) {
      setMismatch(t("The new passwords don't match."));
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
      notify(t('Password changed. Other devices have been signed out.'));
    }
  };

  const setD = (field) => (e) => setDetails({ ...details, [field]: e.target.value });
  const setP = (field) => (e) => setPasswords({ ...passwords, [field]: e.target.value });
  const saveErr = (field) => t(fieldError(save.error, field));
  const changeErr = (field) => t(fieldError(change.error, field));

  return (
    <>
      <PageHeader title={t('My profile')} subtitle={t('Signed in as {username}', { username: user.username })} actions={<StatusChip value={user.role} />} />
      <Box sx={{ display: 'grid', gap: 3, gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, alignItems: 'start' }}>
        {/* [ACCOUNT DETAILS HERE]
            How: A read-only card with the user's username, role, job title,
                 manager, and start date. Salary and the internal ID are left out.
            Why: People should be able to see the facts about their own
                 account, but only an admin can change them, and the
                 requirements make salary visible to admins only. */}
        <Card sx={{ gridColumn: { md: '1 / -1' } }}>
          <CardContent>
            <Typography variant="h6" component="h2">{t('Account details')}</Typography>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              {t('These are managed by an admin.')}
            </Typography>
            <Box sx={{ display: 'grid', columnGap: 4, gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' } }}>
              <DetailRow label={t('Username')}><code>{user.username}</code></DetailRow>
              <DetailRow label={t('Role')}><StatusChip value={user.role} /></DetailRow>
              <DetailRow label={t('Job title')}>{user.job_title || t('Not set')}</DetailRow>
              <DetailRow label={t('Reports to')}>{user.manager_name || t('No manager')}</DetailRow>
              <DetailRow label={t('Member since')}>{formatDate(user.created_at)}</DetailRow>
            </Box>
          </CardContent>
        </Card>

        <Card>
          <CardContent component="form" onSubmit={saveDetails} noValidate>
            <Typography variant="h6" component="h2" gutterBottom>{t('Your details')}</Typography>
            <Stack spacing={2}>
              <ErrorAlert error={save.error} />
              <TextField label={t('First name')} value={details.first_name} onChange={setD('first_name')} error={!!saveErr('first_name')} helperText={saveErr('first_name')} />
              <TextField label={t('Last name')} value={details.last_name} onChange={setD('last_name')} error={!!saveErr('last_name')} helperText={saveErr('last_name')} />
              <TextField label={t('Email')} type="email" value={details.email} onChange={setD('email')} error={!!saveErr('email')} helperText={saveErr('email')} />
              <TextField label={t('Profile picture URL')} value={details.profile_picture_url} onChange={setD('profile_picture_url')}
                error={!!saveErr('profile_picture_url')} helperText={saveErr('profile_picture_url') || t('Optional link to an image (https://...).')} />
              <Box><BusyButton type="submit" variant="contained" busy={save.busy} busyLabel={t('Saving…')}>{t('Save details')}</BusyButton></Box>
            </Stack>
          </CardContent>
        </Card>

        <Card>
          <CardContent component="form" onSubmit={changePassword} noValidate>
            <Typography variant="h6" component="h2" gutterBottom>{t('Change password')}</Typography>
            <Stack spacing={2}>
              {mismatch && <Alert severity="error">{mismatch}</Alert>}
              <ErrorAlert error={change.error} />
              <TextField label={t('Current password')} type="password" autoComplete="current-password" value={passwords.current_password} onChange={setP('current_password')}
                error={!!changeErr('current_password')} helperText={changeErr('current_password')} />
              <TextField label={t('New password')} type="password" autoComplete="new-password" value={passwords.password} onChange={setP('password')}
                error={!!changeErr('password')} helperText={changeErr('password') || t('At least 8 characters with a letter and a number.')} />
              <TextField label={t('Confirm new password')} type="password" autoComplete="new-password" value={passwords.confirm} onChange={setP('confirm')} />
              <Box><BusyButton type="submit" variant="contained" busy={change.busy} busyLabel={t('Changing…')}>{t('Change password')}</BusyButton></Box>
            </Stack>
          </CardContent>
        </Card>
      </Box>
    </>
  );
}
