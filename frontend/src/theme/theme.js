import { createTheme } from '@mui/material/styles';

// [MUI THEME HERE]
// How: buildTheme(mode) builds the "navy command center" look for light or
//      dark mode: ACME navy and white, one amber accent for highlights and
//      risk, Space Grotesk headings over IBM Plex Sans body text, softly
//      rounded cards, and a palette.brand group with the sidebar and timeline
//      colors that custom components read.
// Why: Nearly every visual decision lives here, so pages stay simple and the
//      whole app changes together. Amber is used sparingly (current item,
//      risk, key actions) so it always means "look here".
export const NAVY = '#0b2a5b';
export const NAVY_DEEP = '#081a38';
export const AMBER = '#F5A524';

const HEADING = '"Space Grotesk", "Segoe UI", sans-serif';
const BODY = '"IBM Plex Sans", "Segoe UI", system-ui, sans-serif';

export default function buildTheme(mode) {
  const dark = mode === 'dark';
  const brand = {
    sidebar: dark ? '#06142c' : NAVY_DEEP,
    sidebarText: '#ffffff',
    sidebarMuted: '#c9d4e6',
    sidebarActive: 'rgba(255, 255, 255, 0.10)',
    banner: dark ? '#10264a' : NAVY,
    accent: AMBER,
    accentText: NAVY_DEEP,
    barDone: dark ? '#3d5378' : '#a9b9d3',
    barDoneText: dark ? '#ffffff' : NAVY,
    barActive: dark ? '#7cb8ff' : NAVY,
    barActiveText: dark ? NAVY_DEEP : '#ffffff',
    barPlannedBorder: dark ? '#7cb8ff' : NAVY,
    gridLine: dark ? 'rgba(255, 255, 255, 0.10)' : '#e3e9f2',
    heat: dark
      ? ['#132b52', '#1d4a85', '#2f6bbd', '#7cb8ff', AMBER]
      : ['#f1f5fb', '#cfdcf0', '#8fa9d4', '#2f5597', AMBER],
  };
  return createTheme({
    palette: dark
      ? {
        mode,
        brand,
        primary: { main: '#ffffff', contrastText: NAVY },
        secondary: { main: AMBER, contrastText: NAVY_DEEP },
        warning: { main: AMBER, contrastText: NAVY_DEEP },
        background: { default: NAVY_DEEP, paper: '#10264a' },
        text: { primary: '#ffffff', secondary: 'rgba(255, 255, 255, 0.72)' },
        divider: 'rgba(255, 255, 255, 0.12)',
        action: { selected: 'rgba(124, 184, 255, 0.18)', hover: 'rgba(255, 255, 255, 0.08)' },
      }
      : {
        mode,
        brand,
        primary: { main: NAVY, contrastText: '#ffffff' },
        secondary: { main: AMBER, contrastText: NAVY_DEEP },
        warning: { main: AMBER, contrastText: NAVY_DEEP },
        background: { default: '#f3f6fb', paper: '#ffffff' },
        text: { primary: '#0f1c33', secondary: '#51627f' },
        divider: '#e3e9f2',
        action: { selected: 'rgba(11, 42, 91, 0.08)' },
      },
    shape: { borderRadius: 10 },
    typography: {
      fontFamily: BODY,
      h1: { fontFamily: HEADING, fontWeight: 700 },
      h2: { fontFamily: HEADING, fontWeight: 700 },
      h3: { fontFamily: HEADING, fontWeight: 700 },
      h4: { fontFamily: HEADING, fontWeight: 700, letterSpacing: '-0.5px' },
      h5: { fontFamily: HEADING, fontWeight: 700, letterSpacing: '-0.3px' },
      h6: { fontFamily: HEADING, fontWeight: 700 },
      subtitle1: { fontWeight: 600 },
      button: { textTransform: 'none', fontWeight: 600 },
    },
    components: {
      MuiCard: {
        defaultProps: { variant: 'outlined' },
        styleOverrides: { root: { borderRadius: 18 } },
      },
      MuiPaper: {
        defaultProps: { elevation: 0 },
        styleOverrides: { root: { backgroundImage: 'none' }, outlined: { borderRadius: 18 } },
      },
      MuiCardContent: { styleOverrides: { root: { padding: 22, '&:last-child': { paddingBottom: 22 } } } },
      MuiButton: { styleOverrides: { root: { borderRadius: 10, minHeight: 40 } } },
      MuiChip: { styleOverrides: { root: { fontWeight: 600 } } },
      MuiTextField: { defaultProps: { fullWidth: true, size: 'small' } },
      MuiOutlinedInput: { styleOverrides: { root: { borderRadius: 10 } } },
      MuiTableCell: {
        styleOverrides: {
          head: { fontWeight: 600, color: dark ? 'rgba(255,255,255,0.72)' : '#51627f' },
          root: { borderColor: dark ? 'rgba(255,255,255,0.08)' : '#eef2f8' },
        },
      },
      MuiDialog: { styleOverrides: { paper: { borderRadius: 18 } } },
      MuiLinearProgress: { styleOverrides: { root: { borderRadius: 999 }, bar: { borderRadius: 999 } } },
    },
  });
}
