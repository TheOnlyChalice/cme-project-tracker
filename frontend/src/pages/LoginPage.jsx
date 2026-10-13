import LockOutlinedIcon from '@mui/icons-material/LockOutlined';
import { Alert, Avatar, Box, Card, CardContent, TextField, Typography } from '@mui/material';
import { useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext.js';
import AppearanceControls from '../components/AppearanceControls.jsx';
import BusyButton from '../components/BusyButton.jsx';
import { useLanguage } from '../i18n/LanguageContext.js';
import { errorText } from '../i18n/translate.js';

// [LOGIN PAGE HERE]
// How: Sends the username (or email) and password to /auth/login, then
//      returns the user to the page they were trying to open. Language and
//      dark mode can be chosen before signing in.
// Why: The backend's messages (wrong password, account locked for 15
//      minutes) are shown in the chosen language, so users know exactly what
//      happened.
/** The sign-in page. */
export default function LoginPage() {
  const { user, login, notice } = useAuth();
  const { lang, t } = useLanguage();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ username: '', password: '' });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to={location.state?.from || '/'} replace />;

  const submit = async (event) => {
    event.preventDefault();
    if (!form.username.trim() || !form.password) {
      setError({ message: t('Enter your username and password.') });
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await login(form.username.trim(), form.password);
      navigate(location.state?.from || '/', { replace: true });
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  const update = (field) => (event) => setForm({ ...form, [field]: event.target.value });

  return (
    <Box sx={{ minHeight: '100%', display: 'grid', placeItems: 'center', p: 2, bgcolor: 'background.default', position: 'relative' }}>
      <Box sx={{ position: 'absolute', top: 12, right: 12 }}><AppearanceControls /></Box>
      <Card sx={{ width: '100%', maxWidth: 400 }}>
        <CardContent sx={{ p: 4 }}>
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', mb: 3 }}>
            <Avatar sx={{ bgcolor: 'primary.main', mb: 1 }}><LockOutlinedIcon /></Avatar>
            <Typography variant="h5" component="h1">ACME Project Tracker</Typography>
            <Typography color="text.secondary">{t('Sign in to continue')}</Typography>
          </Box>
          {notice && !error && <Alert severity="info" sx={{ mb: 2 }}>{errorText(notice, lang)}</Alert>}
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error.code ? errorText(error, lang) : error.message}</Alert>}
          <Box component="form" onSubmit={submit} noValidate sx={{ display: 'grid', gap: 2 }}>
            <TextField label={t('Username or email')} value={form.username} onChange={update('username')}
              autoComplete="username" autoFocus size="medium" />
            <TextField label={t('Password')} type="password" value={form.password} onChange={update('password')}
              autoComplete="current-password" size="medium" />
            <BusyButton type="submit" variant="contained" size="large" busy={busy} busyLabel={t('Signing in…')}>
              {t('Sign in')}
            </BusyButton>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
