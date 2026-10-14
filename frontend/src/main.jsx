import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { HashRouter } from 'react-router-dom';
import App from './App.jsx';
import AuthProvider from './auth/AuthProvider.jsx';
import ErrorBoundary from './components/ErrorBoundary.jsx';
import GlobalProgress from './components/GlobalProgress.jsx';
import NotifyProvider from './components/NotifyProvider.jsx';
import LanguageProvider from './i18n/LanguageProvider.jsx';
import './index.css';
import ColorModeProvider from './theme/ColorModeProvider.jsx';

// [ACME: HASH ROUTER HERE]
// How: Page addresses use a # (e.g. /#/projects/123) via HashRouter.
// Why: The site is served from S3 behind CloudFront. With normal addresses,
//      refreshing /projects/123 would ask S3 for a file that doesn't exist and
//      fail; with a #, the browser always loads index.html and React picks
//      the page. No server or CloudFront changes are needed.

// [ACME: PROVIDER ORDER HERE]
// How: Language is outermost, then light/dark theme, the error boundary, the
//      loading bar, routing, messages, and sign-in.
// Why: Each layer can use the ones outside it: the error screen is translated
//      and themed, and every page gets language, theme, and sign-in state.
createRoot(document.getElementById('root')).render(
  <StrictMode>
    <LanguageProvider>
      <ColorModeProvider>
        <ErrorBoundary>
          <GlobalProgress />
          <HashRouter>
            <NotifyProvider>
              <AuthProvider>
                <App />
              </AuthProvider>
            </NotifyProvider>
          </HashRouter>
        </ErrorBoundary>
      </ColorModeProvider>
    </LanguageProvider>
  </StrictMode>,
);
