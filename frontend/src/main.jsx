import CssBaseline from '@mui/material/CssBaseline';
import { ThemeProvider } from '@mui/material/styles';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { HashRouter } from 'react-router-dom';
import App from './App.jsx';
import AuthProvider from './auth/AuthProvider.jsx';
import ErrorBoundary from './components/ErrorBoundary.jsx';
import NotifyProvider from './components/NotifyProvider.jsx';
import './index.css';
import theme from './theme.js';

// [HASH ROUTER HERE]
// How: Page addresses use a # (e.g. /#/projects/123) via HashRouter.
// Why: The site is served from S3 behind CloudFront. With normal addresses,
//      refreshing /projects/123 would ask S3 for a file that doesn't exist and
//      fail; with a #, the browser always loads index.html and React picks
//      the page. No server or CloudFront changes are needed.
createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <ErrorBoundary>
        <HashRouter>
          <NotifyProvider>
            <AuthProvider>
              <App />
            </AuthProvider>
          </NotifyProvider>
        </HashRouter>
      </ErrorBoundary>
    </ThemeProvider>
  </StrictMode>,
);
