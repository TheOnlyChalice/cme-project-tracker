import { createTheme } from '@mui/material/styles';

// [MUI THEME HERE]
// How: buildTheme(mode) creates the Material UI theme for light or dark mode.
//      ACME's brand is dark blue and white: light mode uses white surfaces
//      with dark blue accents, and dark mode flips it to dark blue surfaces
//      with white text and white primary buttons.
// Why: Every component reads its colors from the theme, so both modes share
//      one brand identity, and changing ACME's colors means editing one file.
const NAVY = '#0b2a5b';
const NAVY_DEEP = '#081a38';
const NAVY_SURFACE = '#10264a';
const SKY = '#7cb8ff';

export default function buildTheme(mode) {
  const dark = mode === 'dark';
  return createTheme({
    palette: dark
      ? {
        mode,
        brand: { bar: NAVY_SURFACE },
        primary: { main: '#ffffff', contrastText: NAVY },
        secondary: { main: SKY, contrastText: NAVY_DEEP },
        background: { default: NAVY_DEEP, paper: NAVY_SURFACE },
        text: { primary: '#ffffff', secondary: 'rgba(255, 255, 255, 0.72)' },
        divider: 'rgba(255, 255, 255, 0.14)',
        action: { selected: 'rgba(124, 184, 255, 0.18)', hover: 'rgba(255, 255, 255, 0.08)' },
      }
      : {
        mode,
        brand: { bar: NAVY },
        primary: { main: NAVY, contrastText: '#ffffff' },
        secondary: { main: '#1e6fd9', contrastText: '#ffffff' },
        background: { default: '#f4f7fb', paper: '#ffffff' },
        action: { selected: 'rgba(11, 42, 91, 0.10)' },
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
      MuiPaper: { defaultProps: { elevation: 0 }, styleOverrides: { root: { backgroundImage: 'none' } } },
      MuiTextField: { defaultProps: { fullWidth: true, size: 'small' } },
      MuiTableCell: { styleOverrides: { head: { fontWeight: 600 } } },
    },
  });
}
