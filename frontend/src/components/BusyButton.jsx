import { Button, CircularProgress } from '@mui/material';
import PropTypes from 'prop-types';

// [BUSY BUTTON HERE]
// How: A normal button that, while its action runs, shows a small spinner,
//      switches to a "working" label, and can't be clicked again.
// Why: Shows exactly which action is processing and stops double-clicks
//      from sending the same request twice (for example, assigning hours twice).
/** A button that shows a spinner and disables itself while busy. */
export default function BusyButton({ busy, busyLabel, children, startIcon, disabled, ...props }) {
  return (
    <Button
      {...props}
      disabled={busy || disabled}
      startIcon={busy ? <CircularProgress size={16} color="inherit" /> : startIcon}
      aria-busy={busy || undefined}
    >
      {busy && busyLabel ? busyLabel : children}
    </Button>
  );
}

BusyButton.propTypes = {
  busy: PropTypes.bool,
  busyLabel: PropTypes.node,
  children: PropTypes.node,
  startIcon: PropTypes.node,
  disabled: PropTypes.bool,
};
