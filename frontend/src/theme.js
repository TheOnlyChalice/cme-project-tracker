import { createTheme } from '@mui/material/styles';

// [MUI THEME HERE]
// How: One Material UI theme sets the colors, fonts, corner rounding, and
//      default component styles for the whole app.
// Why: Changing the look (for example, ACME's brand color) means editing this
//      one file instead of every page, and every component stays consistent.
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: '#1f4e79' },
    secondary: { main: '#00897b' },
    background: { default: '#f5f7fa' },
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

export default theme;
