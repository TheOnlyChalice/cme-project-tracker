import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import { Button, IconButton, Stack, Typography } from '@mui/material';
import PropTypes from 'prop-types';
import { useT } from '../i18n/LanguageContext.js';
import { addWeeks, formatDate, mondayOf } from '../utils/format.js';

/** Previous / next week controls, labeled with the week's Monday. */
export default function WeekPicker({ week, onChange }) {
  const t = useT();
  const thisWeek = mondayOf();
  return (
    <Stack direction="row" alignItems="center" spacing={1}>
      <IconButton aria-label={t('Previous week')} onClick={() => onChange(addWeeks(week, -1))}>
        <ChevronLeftIcon />
      </IconButton>
      <Typography sx={{ minWidth: 150, textAlign: 'center' }}>
        {t('Week of {date}', { date: formatDate(week) })}
      </Typography>
      <IconButton aria-label={t('Next week')} onClick={() => onChange(addWeeks(week, 1))}>
        <ChevronRightIcon />
      </IconButton>
      {week !== thisWeek && <Button size="small" onClick={() => onChange(thisWeek)}>{t('This week')}</Button>}
    </Stack>
  );
}

WeekPicker.propTypes = {
  week: PropTypes.string.isRequired,
  onChange: PropTypes.func.isRequired,
};
