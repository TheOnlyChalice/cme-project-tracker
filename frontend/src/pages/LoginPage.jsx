import CheckIcon from '@mui/icons-material/CheckCircleOutline';
import { Alert, AlertTitle, Box, Card, CardContent, Stack, TextField, Typography } from '@mui/material';
import { useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext.js';
import AppearanceControls from '../components/AppearanceControls.jsx';
import BrandMark from '../components/BrandMark.jsx';
import BusyButton from '../components/BusyButton.jsx';
import useIsMobile from '../hooks/useIsMobile.js';
import { useLanguage } from '../i18n/LanguageContext.js';
import { errorStatus, errorText } from '../i18n/translate.js';

const HIGHLIGHTS = [
  'See every project on one timeline',
  'Spot risks before deadlines slip',
  "Plan each person's 40-hour week",
];

// [LOGIN PAGE HERE]
// How: A split screen: a navy brand panel (logo, tagline, three highlights)
//      beside the sign-in card. On phones the panel shrinks to a header.
//      Sends the username (or email) and password to /auth/login, then
//      returns the user to the page they were trying to open. Language and
//      dark mode can be chosen before signing in.
// Why: The login page is the first thing reviewers and users see, so it
//      introduces the ACME brand and what the app does. The backend's own
//      messages (wrong password, locked for 15 minutes) are shown in the
//      chosen language.
/** The sign-in page. */
export default function LoginPage() {
  const { user, login, notice } = useAuth();
  const { lang, t } = useLanguage();
  const isMobile = useIsMobile();
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
    <Box sx={{ minHeight: '100%', display: 'flex', flexDirection: isMobile ? 'column' : 'row', bgcolor: 'background.default' }}>
      <Box component="section" aria-label="ACME"
        sx={{
          flex: isMobile ? '0 0 auto' : '1 1 46%', bgcolor: 'brand.sidebar', color: '#ffffff',
          p: { xs: 3, md: 7 }, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: 4,
        }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <BrandMark size={44} />
          <Box>
            <Typography sx={{ fontFamily: (theme) => theme.typography.h6.fontFamily, fontWeight: 700, fontSize: 22, lineHeight: 1.1 }}>ACME</Typography>
            <Typography sx={{ fontSize: 13, color: 'brand.sidebarMuted' }}>{t('Project Tracker')}</Typography>
          </Box>
        </Box>
        {!isMobile && (
          <Box sx={{ maxWidth: 460 }}>
            <Typography variant="h3" component="p" sx={{ fontSize: 44, lineHeight: 1.1, mb: 2.5 }}>
              {t('Every project, every milestone, every hour.')}
            </Typography>
            <Stack spacing={1.5}>
              {HIGHLIGHTS.map((line) => (
                <Box key={line} sx={{ display: 'flex', alignItems: 'center', gap: 1.25, color: 'brand.sidebarMuted' }}>
                  <CheckIcon sx={{ color: 'brand.accent' }} />
                  <Typography>{t(line)}</Typography>
                </Box>
              ))}
            </Stack>
          </Box>
        )}
        {!isMobile && <Typography variant="body2" sx={{ color: 'brand.sidebarMuted' }}>© ACME Inc.</Typography>}
      </Box>

      <Box sx={{ flex: '1 1 54%', position: 'relative', display: 'grid', placeItems: 'center', p: { xs: 2, md: 6 } }}>
        <Box sx={{ position: 'absolute', top: 16, right: 16 }}><AppearanceControls /></Box>
        <Card sx={{ width: '100%', maxWidth: 420, mt: isMobile ? 6 : 0 }}>
          <CardContent sx={{ p: { xs: 3, md: 4 } }}>
            <Typography variant="h4" component="h1" gutterBottom>{t('Welcome back')}</Typography>
            <Typography color="text.secondary" sx={{ mb: 3 }}>{t('Sign in to continue')}</Typography>
            {notice && !error && (
              <Alert severity="info" sx={{ mb: 2 }}>
                {errorStatus(notice, lang) && <AlertTitle sx={{ mb: 0.25 }}>{errorStatus(notice, lang)}</AlertTitle>}
                {errorText(notice, lang)}
              </Alert>
            )}
            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error.code && errorStatus(error, lang) && <AlertTitle sx={{ mb: 0.25 }}>{errorStatus(error, lang)}</AlertTitle>}
                {error.code ? errorText(error, lang) : error.message}
              </Alert>
            )}
            <Box component="form" onSubmit={submit} noValidate sx={{ display: 'grid', gap: 2 }}>
              <TextField label={t('Username or email')} value={form.username} onChange={update('username')}
                autoComplete="username" autoFocus size="medium" />
              <TextField label={t('Password')} type="password" value={form.password} onChange={update('password')}
                autoComplete="current-password" size="medium" />
              <BusyButton type="submit" variant="contained" size="large" busy={busy} busyLabel={t('Signing in…')} sx={{ minHeight: 48 }}>
                {t('Sign in')}
              </BusyButton>
            </Box>
          </CardContent>
        </Card>
      </Box>
    </Box>
  );
}
