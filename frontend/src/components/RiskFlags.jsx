import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import { Chip, Stack, Tooltip } from '@mui/material';
import PropTypes from 'prop-types';

const SHORT = {
  past_end_date: 'Past end date',
  overdue_milestone: 'Overdue milestone',
  deadline_near: 'Deadline near',
  behind_schedule: 'Behind schedule',
  no_milestones: 'No milestones',
  over_budget: 'Over budget',
  hours_nearly_used: 'Hours nearly used',
};

// [RISK FLAG CHIPS HERE]
// How: Each risk flag from the backend becomes a short warning chip; hovering
//      (or long-pressing on a phone) shows the full reason.
// Why: Managers can scan a list and immediately see *why* a project is at
//      risk, not just that it is.
/** Shows a project's risk flags as chips, or "On track". */
export default function RiskFlags({ flags }) {
  if (!flags?.length) return <Chip size="small" label="On track" color="success" variant="outlined" />;
  return (
    <Stack direction="row" spacing={0.5} useFlexGap sx={{ flexWrap: 'wrap' }}>
      {flags.map((flag) => (
        <Tooltip key={flag.code} title={flag.message}>
          <Chip size="small" color="warning" icon={<WarningAmberIcon />} label={SHORT[flag.code] || flag.code} />
        </Tooltip>
      ))}
    </Stack>
  );
}

RiskFlags.propTypes = {
  flags: PropTypes.arrayOf(PropTypes.shape({ code: PropTypes.string, message: PropTypes.string })),
};
