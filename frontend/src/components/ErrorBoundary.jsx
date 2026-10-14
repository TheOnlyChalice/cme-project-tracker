import { Alert, Box, Button } from '@mui/material';
import PropTypes from 'prop-types';
import { Component } from 'react';
import { LanguageContext } from '../i18n/LanguageContext.js';

// [ACME: ERROR BOUNDARY HERE]
// How: Catches unexpected errors while drawing a page and shows a friendly
//      message with a reload button instead of a blank screen.
// Why: One broken component shouldn't take down the whole app, and a reload
//      usually recovers.
/** Catches page errors and shows a recovery message. */
export default class ErrorBoundary extends Component {
  static contextType = LanguageContext;

  constructor(props) {
    super(props);
    this.state = { failed: false };
  }

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error, info) {
    console.error('Page error:', error, info);
  }

  render() {
    if (!this.state.failed) return this.props.children;
    const { t } = this.context;
    return (
      <Box sx={{ p: 4 }}>
        <Alert severity="error" action={<Button color="inherit" onClick={() => window.location.reload()}>{t('Reload')}</Button>}>
          {t('Something went wrong displaying this page.')}
        </Alert>
      </Box>
    );
  }
}

ErrorBoundary.propTypes = {
  children: PropTypes.node,
};
