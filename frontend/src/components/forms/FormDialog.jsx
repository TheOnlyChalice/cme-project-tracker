import { Button, Dialog, DialogActions, DialogContent, DialogTitle } from '@mui/material';
import PropTypes from 'prop-types';
import useIsMobile from '../../hooks/useIsMobile.js';
import ErrorAlert from '../ErrorAlert.jsx';

// [FORM DIALOG HERE]
// How: A shared dialog shell for every create/edit form: title, fields,
//      Cancel/Save buttons, a busy state, and the error from the backend. On
//      phones it opens full screen.
// Why: Every form behaves the same way, and small screens get room to type
//      instead of a cramped pop-up.
/** Shared dialog shell for create and edit forms. */
export default function FormDialog({ open, title, onClose, onSubmit, busy, error, submitLabel = 'Save', children }) {
  const isMobile = useIsMobile();
  const generalError = error && !Object.keys(error.details || {}).length ? error : null;
  return (
    <Dialog open={open} onClose={busy ? undefined : onClose} fullWidth maxWidth="sm" fullScreen={isMobile}>
      <form
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit();
        }}
      >
        <DialogTitle>{title}</DialogTitle>
        <DialogContent sx={{ display: 'grid', gap: 2, pt: '8px !important' }}>
          {error && Object.keys(error.details || {}).length > 0 && (
            <ErrorAlert error={{ message: error.message || 'Please fix the highlighted fields.' }} />
          )}
          <ErrorAlert error={generalError} />
          {children}
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose} disabled={busy}>Cancel</Button>
          <Button type="submit" variant="contained" disabled={busy}>{busy ? 'Saving…' : submitLabel}</Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}

FormDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  title: PropTypes.node.isRequired,
  onClose: PropTypes.func.isRequired,
  onSubmit: PropTypes.func.isRequired,
  busy: PropTypes.bool,
  error: PropTypes.object,
  submitLabel: PropTypes.string,
  children: PropTypes.node,
};
