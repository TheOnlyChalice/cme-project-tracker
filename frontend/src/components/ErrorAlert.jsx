import { Alert, Button } from '@mui/material';
import PropTypes from 'prop-types';

// [ERROR DISPLAY HERE]
// How: Shows the backend's own error message, with an optional Retry button.
// Why: The backend already writes clear, specific messages (for example,
//      "This employee has 10 of 40 hours left"), so showing them directly is
//      more useful than a generic "Something went wrong".
/** Shows an API error message with an optional Retry button. */
export default function ErrorAlert({ error, onRetry }) {
  if (!error) return null;
  return (
    <Alert
      severity="error"
      sx={{ my: 2 }}
      action={onRetry && <Button color="inherit" size="small" onClick={onRetry}>Retry</Button>}
    >
      {error.message || 'Something went wrong.'}
    </Alert>
  );
}

ErrorAlert.propTypes = {
  error: PropTypes.shape({ message: PropTypes.string }),
  onRetry: PropTypes.func,
};
