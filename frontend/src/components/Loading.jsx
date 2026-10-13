import { Box, CircularProgress, Typography } from '@mui/material';
import PropTypes from 'prop-types';

/** A centered spinner with an accessible label. */
export default function Loading({ label = 'Loading' }) {
  return (
    <Box role="status" sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 2, py: 6 }}>
      <CircularProgress size={28} />
      <Typography color="text.secondary">{label}…</Typography>
    </Box>
  );
}

Loading.propTypes = {
  label: PropTypes.string,
};
