import CssBaseline from '@mui/material/CssBaseline';
import { ThemeProvider } from '@mui/material/styles';
import PropTypes from 'prop-types';
import { useCallback, useMemo, useState } from 'react';
import { useMediaQuery } from 'react-responsive';
import { ColorModeContext } from './ColorModeContext.js';
import buildTheme from './theme.js';

const KEY = 'acme.colorMode';

// [DARK MODE HERE]
// How: Until someone picks a mode, the app follows the computer's own light or
//      dark setting (read with React Responsive's media query). Using the
//      toggle saves the choice in the browser, and the theme is rebuilt for
//      that mode.
// Why: People who already use dark mode get it automatically, anyone can
//      override it, and the choice is remembered next time.
export default function ColorModeProvider({ children }) {
  const systemDark = useMediaQuery({ query: '(prefers-color-scheme: dark)' });
  const [chosen, setChosen] = useState(() => localStorage.getItem(KEY));
  const mode = chosen || (systemDark ? 'dark' : 'light');

  const toggle = useCallback(() => {
    const next = mode === 'dark' ? 'light' : 'dark';
    localStorage.setItem(KEY, next);
    setChosen(next);
  }, [mode]);

  const theme = useMemo(() => buildTheme(mode), [mode]);
  const value = useMemo(() => ({ mode, toggle }), [mode, toggle]);

  return (
    <ColorModeContext.Provider value={value}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </ColorModeContext.Provider>
  );
}

ColorModeProvider.propTypes = {
  children: PropTypes.node,
};
