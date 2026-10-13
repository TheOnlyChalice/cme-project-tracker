import { Alert, Box, Checkbox, FormControlLabel, Typography } from '@mui/material';
import PropTypes from 'prop-types';
import { useT } from '../../i18n/LanguageContext.js';
import { formatDate } from '../../utils/format.js';

// [SHIFT OPTIONS HERE]
// How: Shown in the milestone and project forms when a date change could
//      move other milestones. One checkbox (ticked by default) moves them,
//      with a preview of their new dates; a second checkbox appears only if
//      the moved milestones would run past the project's end date.
// Why: Your rule: later milestones should follow automatically, but as a
//      choice, so an intentional gap isn't lost. The preview shows exactly
//      what will change before saving, and extending the deadline is never
//      done silently.
/** Checkboxes and preview for moving later milestones with a date change. */
export default function ShiftOptions({ moves, days, shift, onShiftChange, overflowEnd, extend, onExtendChange, label }) {
  const t = useT();
  if (!moves.length && !overflowEnd) return null;
  const amount = days > 0 ? t('{days} days later', { days }) : t('{days} days earlier', { days: Math.abs(days) });
  return (
    <Alert severity="info" icon={false}>
      {moves.length > 0 && (
        <>
          <FormControlLabel
            control={<Checkbox checked={shift} onChange={(e) => onShiftChange(e.target.checked)} />}
            label={t(label, { count: moves.length, amount })}
          />
          {shift && (
            <Box component="ul" sx={{ m: 0, pl: 4 }}>
              {moves.map((m) => (
                <Typography component="li" variant="body2" key={m.id}>
                  {m.sequence}. {m.name}: {formatDate(m.start)} – {formatDate(m.end)}
                </Typography>
              ))}
            </Box>
          )}
        </>
      )}
      {overflowEnd && (
        <FormControlLabel
          control={<Checkbox checked={extend} onChange={(e) => onExtendChange(e.target.checked)} />}
          label={t("Extend the project's end date to {date} to fit", { date: formatDate(overflowEnd) })}
        />
      )}
    </Alert>
  );
}

ShiftOptions.propTypes = {
  moves: PropTypes.arrayOf(PropTypes.object).isRequired,
  days: PropTypes.number.isRequired,
  shift: PropTypes.bool.isRequired,
  onShiftChange: PropTypes.func.isRequired,
  overflowEnd: PropTypes.string,
  extend: PropTypes.bool.isRequired,
  onExtendChange: PropTypes.func.isRequired,
  label: PropTypes.string.isRequired,
};
