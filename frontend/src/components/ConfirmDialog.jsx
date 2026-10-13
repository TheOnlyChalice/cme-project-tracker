import { Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle } from '@mui/material';
import { useState } from 'react';
import PropTypes from 'prop-types';
import ErrorAlert from './ErrorAlert.jsx';

// [CONFIRM DIALOG HERE]
// How: Asks "Are you sure?" before an action runs, shows a spinner while it
//      runs, and keeps the dialog open with the error if it fails.
// Why: Completing, abandoning, or archiving can't be undone by most users,
//      so a deliberate second click prevents accidents.
/** An "are you sure?" dialog that runs an action and shows its errors. */
export default function ConfirmDialog({ open, title, message, confirmLabel = 'Confirm', color = 'primary', onConfirm, onClose }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const run = async () => {
    setBusy(true);
    setError(null);
    try {
      await onConfirm();
      onClose();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onClose={busy ? undefined : onClose} maxWidth="xs" fullWidth>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <DialogContentText>{message}</DialogContentText>
        <ErrorAlert error={error} />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={busy}>Cancel</Button>
        <Button variant="contained" color={color} onClick={run} disabled={busy}>
          {busy ? 'Working…' : confirmLabel}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

ConfirmDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  title: PropTypes.node,
  message: PropTypes.node,
  confirmLabel: PropTypes.string,
  color: PropTypes.string,
  onConfirm: PropTypes.func.isRequired,
  onClose: PropTypes.func.isRequired,
};
