import { Alert, Button } from '@mui/material';
import PropTypes from 'prop-types';
import { useLanguage } from '../i18n/LanguageContext.js';
import { errorText } from '../i18n/translate.js';

// [ERROR DISPLAY HERE]
// How: Shows the backend's error in the chosen language (rebuilt from its
//      error code), with an optional Retry button.
// Why: The backend's messages are specific (for example, "This employee only
//      has 10 hours left that week"), so showing them is more useful than a
//      generic "Something went wrong".
/** Shows an API error message with an optional Retry button. */
export default function ErrorAlert({ error, onRetry }) {
  const { lang, t } = useLanguage();
  if (!error) return null;
  return (
    <Alert
      severity="error"
      sx={{ my: 2 }}
      action={onRetry && <Button color="inherit" size="small" onClick={onRetry}>{t('Retry')}</Button>}
    >
      {errorText(error, lang)}
    </Alert>
  );
}

ErrorAlert.propTypes = {
  error: PropTypes.shape({ message: PropTypes.string, code: PropTypes.string }),
  onRetry: PropTypes.func,
};
