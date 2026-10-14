import { Box, ButtonBase, Typography } from '@mui/material';
import { useTheme } from '@mui/material/styles';
import { PieChart } from '@mui/x-charts/PieChart';
import PropTypes from 'prop-types';
import { useT } from '../../i18n/LanguageContext.js';

export const STATUS_CATEGORIES = ['on_track', 'at_risk', 'inactive', 'no_milestones'];
const LABELS = { on_track: 'On track', at_risk: 'At risk', inactive: 'Inactive', no_milestones: 'No milestones' };

/** Put a project into exactly one health category from its risk flags. */
export function statusCategory(project) {
  const codes = (project.risk_flags || []).map((flag) => flag.code);
  if (codes.includes('no_milestones')) return 'no_milestones';
  if (codes.some((code) => code !== 'inactive')) return 'at_risk';
  if (codes.includes('inactive')) return 'inactive';
  return 'on_track';
}

// [STATUS DONUT HERE]
// How: A ring chart (MUI X Charts) splitting active projects into on track,
//      at risk, inactive, and no milestones, with the total in the middle.
//      Clicking a slice, or its legend entry, filters the timeline below to
//      those projects; clicking it again clears the filter.
// Why: Answers "how healthy is the portfolio?" at a glance, and doubles as
//      the quickest way to narrow the timeline. The legend entries are real
//      buttons so it also works from the keyboard.
/** Clickable donut of project health categories. */
export default function StatusDonut({ projects, selected, onSelect }) {
  const t = useT();
  const theme = useTheme();
  const colors = {
    on_track: theme.palette.brand.barActive,
    at_risk: theme.palette.brand.accent,
    inactive: theme.palette.brand.heat[2],
    no_milestones: theme.palette.brand.heat[1],
  };
  const counts = Object.fromEntries(STATUS_CATEGORIES.map((c) => [c, 0]));
  projects.forEach((p) => { counts[statusCategory(p)] += 1; });
  const data = STATUS_CATEGORIES.filter((c) => counts[c] > 0).map((c) => ({
    id: c, value: counts[c], label: t(LABELS[c]), color: colors[c],
  }));
  const toggle = (category) => onSelect(selected === category ? 'all' : category);

  return (
    <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 2 }}>
      <Box sx={{ position: 'relative', width: 190, height: 190, mx: 'auto' }}>
        <PieChart
          width={190}
          height={190}
          hideLegend
          margin={{ top: 0, bottom: 0, left: 0, right: 0 }}
          series={[{
            data,
            innerRadius: 62,
            outerRadius: 92,
            paddingAngle: 2,
            cornerRadius: 4,
            highlightScope: { fade: 'global', highlight: 'item' },
          }]}
          onItemClick={(_, item) => data[item.dataIndex] && toggle(data[item.dataIndex].id)}
        />
        <Box sx={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', pointerEvents: 'none' }}>
          <Typography variant="h4" component="p">{projects.length}</Typography>
          <Typography variant="body2" color="text.secondary">{t('active projects')}</Typography>
        </Box>
      </Box>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75, flex: '1 1 160px' }}>
        {STATUS_CATEGORIES.map((c) => (
          <ButtonBase key={c} onClick={() => toggle(c)} disabled={!counts[c]} aria-pressed={selected === c}
            sx={{
              justifyContent: 'flex-start', gap: 1.25, px: 1.25, py: 0.75, borderRadius: 2, textAlign: 'left',
              bgcolor: selected === c ? 'action.selected' : 'transparent', opacity: counts[c] ? 1 : 0.5,
              '&:hover': { bgcolor: 'action.hover' },
            }}>
            <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: colors[c], flexShrink: 0 }} />
            <Typography variant="body2" sx={{ flexGrow: 1 }}>{t(LABELS[c])}</Typography>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>{counts[c]}</Typography>
          </ButtonBase>
        ))}
      </Box>
    </Box>
  );
}

StatusDonut.propTypes = {
  projects: PropTypes.arrayOf(PropTypes.object).isRequired,
  selected: PropTypes.string.isRequired,
  onSelect: PropTypes.func.isRequired,
};
