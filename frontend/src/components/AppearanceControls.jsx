import DarkModeIcon from '@mui/icons-material/DarkModeOutlined';
import LightModeIcon from '@mui/icons-material/LightModeOutlined';
import { IconButton, Stack, ToggleButton, ToggleButtonGroup, Tooltip } from '@mui/material';
import PropTypes from 'prop-types';
import { useLanguage } from '../i18n/LanguageContext.js';
import { useColorMode } from '../theme/ColorModeContext.js';

// [APPEARANCE CONTROLS HERE]
// How: A sun/moon button switches light and dark mode, and an EN | ES switch
//      changes the language. Both are in the top bar and on the login page.
// Why: Keeping both in one small component means they look and behave the
//      same everywhere, and people can choose before they even sign in.
/** Light/dark mode button and English/Spanish switch. */
export default function AppearanceControls({ inverse = false }) {
  const { mode, toggle } = useColorMode();
  const { lang, setLang, t } = useLanguage();
  const dark = mode === 'dark';
  // On the dark blue top bar, the controls are drawn in white.
  const toggleSx = inverse ? {
    px: 1, py: 0.25, color: 'rgba(255, 255, 255, 0.8)', borderColor: 'rgba(255, 255, 255, 0.4)',
    '&.Mui-selected, &.Mui-selected:hover': { color: '#ffffff', bgcolor: 'rgba(255, 255, 255, 0.2)' },
  } : { px: 1, py: 0.25 };
  return (
    <Stack direction="row" spacing={1} alignItems="center">
      <ToggleButtonGroup
        size="small"
        exclusive
        value={lang}
        onChange={(_, next) => next && setLang(next)}
        aria-label={t('Language')}
      >
        <ToggleButton value="en" aria-label="English" sx={toggleSx}>EN</ToggleButton>
        <ToggleButton value="es" aria-label="Español" sx={toggleSx}>ES</ToggleButton>
      </ToggleButtonGroup>
      <Tooltip title={dark ? t('Switch to light mode') : t('Switch to dark mode')}>
        <IconButton onClick={toggle} color={inverse ? 'inherit' : 'default'} aria-label={dark ? t('Switch to light mode') : t('Switch to dark mode')}>
          {dark ? <LightModeIcon /> : <DarkModeIcon />}
        </IconButton>
      </Tooltip>
    </Stack>
  );
}

AppearanceControls.propTypes = {
  inverse: PropTypes.bool,
};
