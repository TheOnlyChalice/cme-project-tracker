import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import { Chip, Stack, Tooltip } from '@mui/material';
import PropTypes from 'prop-types';
import { useLanguage } from '../i18n/LanguageContext.js';
import { FLAG_LABELS, flagText } from '../i18n/translate.js';

// [RISK FLAG CHIPS HERE]
// How: Each risk flag from the backend becomes a short warning chip; hovering
//      (or long-pressing on a phone) shows the full reason in the chosen language.
// Why: Managers can scan a list and immediately see *why* a project is at
//      risk, not just that it is.
/** Shows a project's risk flags as chips, or "On track". */
export default function RiskFlags({ flags }) {
  const { lang, t } = useLanguage();
  if (!flags?.length) return <Chip size="small" label={t('On track')} color="success" variant="outlined" />;
  return (
    <Stack direction="row" spacing={0.5} useFlexGap sx={{ flexWrap: 'wrap' }}>
      {flags.map((flag) => (
        <Tooltip key={flag.code} title={flagText(flag, lang)}>
          <Chip size="small" color="warning" icon={<WarningAmberIcon />} label={t(FLAG_LABELS[flag.code] || flag.code)} />
        </Tooltip>
      ))}
    </Stack>
  );
}

RiskFlags.propTypes = {
  flags: PropTypes.arrayOf(PropTypes.shape({ code: PropTypes.string, message: PropTypes.string, params: PropTypes.object })),
};
