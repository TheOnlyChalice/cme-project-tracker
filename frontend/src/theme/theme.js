import { createTheme } from '@mui/material/styles';

// [MUI THEME HERE]
// How: buildTheme(mode) creates the Material UI theme for light or dark mode:
//      colors, fonts, corner rounding, and default component styles.
// Why: Every component reads its colors from the theme, so switching modes
//      re-colors the whole app at once, and changing ACME's brand color means
//      editing one place.
export default function buildTheme(mode) {
  const dark = mode === 'dark';
  return createTheme({
    palette: {
      mode,
      primary: { main: dark ? '#7fb3e6' : '#1f4e79' },
      secondary: { main: dark ? '#4db6ac' : '#00897b' },
      background: dark
        ? { default: '#0f1720', paper: '#16202b' }
        : { default: '#f5f7fa', paper: '#ffffff' },
    },
    shape: { borderRadius: 10 },
    typography: {
      fontFamily: '"Inter", "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
      h4: { fontWeight: 600 },
      h5: { fontWeight: 600 },
      h6: { fontWeight: 600 },
      button: { textTransform: 'none', fontWeight: 600 },
    },
    components: {
      MuiCard: { defaultProps: { variant: 'outlined' } },
      MuiPaper: { defaultProps: { elevation: 0 } },
      MuiTextField: { defaultProps: { fullWidth: true, size: 'small' } },
      MuiTableCell: { styleOverrides: { head: { fontWeight: 600 } } },
    },
  });
}
