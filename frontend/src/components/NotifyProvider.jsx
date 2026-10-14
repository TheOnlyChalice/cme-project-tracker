import { Alert, Snackbar } from '@mui/material';
import { useCallback, useState } from 'react';
import PropTypes from 'prop-types';
import { NotifyContext } from './NotifyContext.js';

// [ACME: TOAST MESSAGES HERE]
// How: Any page can call notify("Project saved") to show a short message
//      that disappears by itself.
// Why: Confirms that an action worked without interrupting the user with a
//      dialog they have to close.
/** Lets any component show a short success or error message. */
export default function NotifyProvider({ children }) {
  const [message, setMessage] = useState(null);
  const notify = useCallback((text, severity = 'success') => setMessage({ text, severity, id: Date.now() }), []);
  return (
    <NotifyContext.Provider value={notify}>
      {children}
      <Snackbar
        key={message?.id}
        open={Boolean(message)}
        autoHideDuration={3500}
        onClose={() => setMessage(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        {message ? (
          <Alert severity={message.severity} variant="filled" onClose={() => setMessage(null)}>
            {message.text}
          </Alert>
        ) : undefined}
      </Snackbar>
    </NotifyContext.Provider>
  );
}

NotifyProvider.propTypes = {
  children: PropTypes.node,
};
