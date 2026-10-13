import { Box, LinearProgress, Typography } from '@mui/material';
import PropTypes from 'prop-types';

/** A small labeled progress bar; turns red when over 100%. */
export default function ProgressCell({ value, label }) {
  if (value === null || value === undefined) return <Typography color="text.secondary">—</Typography>;
  const number = Number(value);
  return (
    <Box sx={{ minWidth: 110 }}>
      <Typography variant="body2">{label ?? `${Math.round(number)}%`}</Typography>
      <LinearProgress
        variant="determinate"
        value={Math.min(number, 100)}
        color={number > 100 ? 'error' : number >= 90 ? 'warning' : 'primary'}
        sx={{ height: 6, borderRadius: 3 }}
        aria-label={label ?? `${Math.round(number)} percent`}
      />
    </Box>
  );
}

ProgressCell.propTypes = {
  value: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
  label: PropTypes.node,
};
