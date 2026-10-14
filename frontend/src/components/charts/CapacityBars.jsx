import { Box } from '@mui/material';
import { useTheme } from '@mui/material/styles';
import { BarChart } from '@mui/x-charts/BarChart';
import PropTypes from 'prop-types';
import { useT } from '../../i18n/LanguageContext.js';
import { formatDate, formatHours } from '../../utils/format.js';

// [CAPACITY BARS HERE]
// How: One stacked bar per week (MUI X Charts): booked hours in navy, free
//      hours in a light shade, for everyone currently shown in the heat map.
//      Clicking a week's bar selects that week, just like the heat map.
// Why: Answers "when does the team have room for new work?" before anyone
//      reads individual rows, and stays in sync with the heat map filters.
/** Booked versus free team hours per week. */
export default function CapacityBars({ weeks, people, selectedWeek, onSelectWeek }) {
  const t = useT();
  const theme = useTheme();
  const booked = weeks.map((_, i) => people.reduce((sum, p) => sum + Number(p.weeks[i]?.hours || 0), 0));
  const free = booked.map((value) => Math.max(people.length * 40 - value, 0));
  const labels = weeks.map((w) => (w === selectedWeek ? `▸ ${formatDate(w).replace(/,? \d{4}$/, '')}` : formatDate(w).replace(/,? \d{4}$/, '')));

  return (
    <Box>
      <BarChart
        height={230}
        xAxis={[{ scaleType: 'band', data: labels }]}
        yAxis={[{ valueFormatter: (v) => formatHours(v) }]}
        series={[
          { id: 'booked', label: t('Booked'), data: booked, stack: 'total', color: theme.palette.brand.barActive, valueFormatter: (v) => formatHours(v) },
          { id: 'free', label: t('Free'), data: free, stack: 'total', color: theme.palette.brand.heat[1], valueFormatter: (v) => formatHours(v) },
        ]}
        onAxisClick={(_, data) => {
          if (data && weeks[data.dataIndex]) onSelectWeek(weeks[data.dataIndex]);
        }}
        margin={{ left: 60, right: 16, top: 16, bottom: 30 }}
      />
    </Box>
  );
}

CapacityBars.propTypes = {
  weeks: PropTypes.arrayOf(PropTypes.string).isRequired,
  people: PropTypes.arrayOf(PropTypes.shape({ weeks: PropTypes.array.isRequired })).isRequired,
  selectedWeek: PropTypes.string,
  onSelectWeek: PropTypes.func.isRequired,
};
