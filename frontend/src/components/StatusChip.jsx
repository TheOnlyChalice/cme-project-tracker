import { Chip } from '@mui/material';
import PropTypes from 'prop-types';

const COLORS = {
  active: 'primary',
  completed: 'success',
  abandoned: 'default',
  archived: 'default',
  admin: 'secondary',
  manager: 'primary',
  employee: 'default',
  fully_booked: 'error',
  partly_booked: 'warning',
  unassigned: 'success',
  locked: 'error',
};

const LABELS = {
  fully_booked: 'Fully booked',
  partly_booked: 'Partly booked',
  unassigned: 'Available',
};

/** A small colored label for statuses, roles, and booking states. */
export default function StatusChip({ value, archived = false }) {
  if (archived) return <Chip size="small" label="Archived" variant="outlined" />;
  const label = LABELS[value] || (value ? value[0].toUpperCase() + value.slice(1) : '—');
  return <Chip size="small" label={label} color={COLORS[value] || 'default'} />;
}

StatusChip.propTypes = {
  value: PropTypes.string,
  archived: PropTypes.bool,
};
