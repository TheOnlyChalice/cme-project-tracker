import { Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle } from '@mui/material';
import PropTypes from 'prop-types';
import { useState } from 'react';
import { useT } from '../i18n/LanguageContext.js';
import BusyButton from './BusyButton.jsx';
import ErrorAlert from './ErrorAlert.jsx';

// [CONFIRM DIALOG HERE]
// How: Asks "Are you sure?" before an action runs, shows a spinner on the
//      button while it runs, and keeps the dialog open with the error if it fails.
// Why: Completing, abandoning, or archiving can't be undone by most users,
//      so a deliberate second click prevents accidents.
/** An "are you sure?" dialog that runs an action and shows its errors. */
export default function ConfirmDialog({ open, title, message, confirmLabel = 'Confirm', color = 'primary', onConfirm, onClose }) {
  const t = useT();
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
        <Button onClick={onClose} disabled={busy}>{t('Cancel')}</Button>
        <BusyButton variant="contained" color={color} onClick={run} busy={busy} busyLabel={t('Working…')}>
          {t(confirmLabel)}
        </BusyButton>
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
