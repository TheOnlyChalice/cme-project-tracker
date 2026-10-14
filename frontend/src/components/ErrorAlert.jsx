import { Alert, AlertTitle, Button } from '@mui/material';
import PropTypes from 'prop-types';
import { useLanguage } from '../i18n/LanguageContext.js';
import { errorStatus, errorText } from '../i18n/translate.js';

// [ERROR DISPLAY HERE]
// How: Shows the error's HTTP status code as the title (for example
//      "Error 409"), then the backend's message in the chosen language, with
//      an optional Retry button.
// Why: The code says what kind of problem it is; the message says exactly
//      what to do about it (for example, "This employee only has 10 hours
//      left that week").
/** Shows an API error with its status code and an optional Retry button. */
export default function ErrorAlert({ error, onRetry }) {
  const { lang, t } = useLanguage();
  if (!error) return null;
  const status = errorStatus(error, lang);
  return (
    <Alert
      severity="error"
      sx={{ my: 2 }}
      action={onRetry && <Button color="inherit" size="small" onClick={onRetry}>{t('Retry')}</Button>}
    >
      {status && <AlertTitle sx={{ mb: 0.25 }}>{status}</AlertTitle>}
      {errorText(error, lang)}
    </Alert>
  );
}

ErrorAlert.propTypes = {
  error: PropTypes.shape({ message: PropTypes.string, code: PropTypes.string, status: PropTypes.number }),
  onRetry: PropTypes.func,
};
