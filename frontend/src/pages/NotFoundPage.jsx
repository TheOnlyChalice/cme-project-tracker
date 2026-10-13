import { Box, Button, Typography } from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import { useT } from '../i18n/LanguageContext.js';

/** Shown for addresses that don't match any page. */
export default function NotFoundPage() {
  const t = useT();
  return (
    <Box sx={{ textAlign: 'center', py: 8 }}>
      <Typography variant="h4" component="h1" gutterBottom>{t('Page not found')}</Typography>
      <Typography color="text.secondary" sx={{ mb: 3 }}>
        {t('It may have been moved, archived, or you may not have access to it.')}
      </Typography>
      <Button variant="contained" component={RouterLink} to="/">{t('Back to dashboard')}</Button>
    </Box>
  );
}
