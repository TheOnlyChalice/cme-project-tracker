import { Chip } from '@mui/material';
import PropTypes from 'prop-types';
import { useT } from '../i18n/LanguageContext.js';

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
  active: 'Active',
  completed: 'Completed',
  abandoned: 'Abandoned',
  admin: 'Admin',
  manager: 'Manager',
  employee: 'Employee',
  fully_booked: 'Fully booked',
  partly_booked: 'Partly booked',
  unassigned: 'Available',
  locked: 'Locked',
};

/** A small colored label for statuses, roles, and booking states. */
export default function StatusChip({ value, archived = false }) {
  const t = useT();
  if (archived) return <Chip size="small" label={t('Archived')} variant="outlined" />;
  return <Chip size="small" label={t(LABELS[value] || value || '—')} color={COLORS[value] || 'default'} />;
}

StatusChip.propTypes = {
  value: PropTypes.string,
  archived: PropTypes.bool,
};
