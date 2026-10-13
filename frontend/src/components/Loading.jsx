import { Box, CircularProgress, Typography } from '@mui/material';
import PropTypes from 'prop-types';
import { useT } from '../i18n/LanguageContext.js';

/** A centered spinner with an accessible label. */
export default function Loading({ label = 'Loading' }) {
  const t = useT();
  return (
    <Box role="status" sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 2, py: 6 }}>
      <CircularProgress size={28} />
      <Typography color="text.secondary">{t(label)}…</Typography>
    </Box>
  );
}

Loading.propTypes = {
  label: PropTypes.string,
};
