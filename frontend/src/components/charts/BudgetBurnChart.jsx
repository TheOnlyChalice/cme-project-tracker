import { Alert, Box } from '@mui/material';
import { useTheme } from '@mui/material/styles';
import { LineChart } from '@mui/x-charts/LineChart';
import PropTypes from 'prop-types';
import { useT } from '../../i18n/LanguageContext.js';
import { formatDate, formatMoney } from '../../utils/format.js';

// [ACME: BUDGET BURN CHART HERE]
// How: A line chart of labor cost adding up week by week: a solid navy line
//      for cost so far, a dashed amber line for the forecast from booked
//      hours, and a dashed red line for the budget. A short sentence above
//      says whether, and in which week, the forecast crosses the budget.
// Why: Turns "budget used versus planned" from a single number into a
//      picture of when the money runs out, which is the question managers and
//      admins actually ask.
/** Cumulative labor cost against the budget, week by week. */
export default function BudgetBurnChart({ series }) {
  const t = useT();
  const theme = useTheme();
  const budget = series.budget === null || series.budget === undefined ? null : Number(series.budget);
  const labels = series.weeks.map((w) => formatDate(w).replace(/,? \d{4}$/, ''));
  const money = (value) => (value === null || value === undefined ? '' : formatMoney(value));
  const totals = series.weeks.map((_, i) => Number(series.forecast[i] ?? series.to_date[i] ?? 0));
  const crossing = budget === null ? -1 : totals.findIndex((value) => value > budget);

  const lines = [
    { id: 'to_date', label: t('Cost so far'), data: series.to_date.map((v) => (v === null ? null : Number(v))), color: theme.palette.brand.barActive, showMark: false, valueFormatter: money },
    { id: 'forecast', label: t('Forecast'), data: series.forecast.map((v) => (v === null ? null : Number(v))), color: theme.palette.brand.accent, showMark: false, valueFormatter: money },
  ];
  if (budget !== null) {
    lines.push({ id: 'budget', label: t('Budget'), data: series.weeks.map(() => budget), color: theme.palette.error.main, showMark: false, valueFormatter: money });
  }

  return (
    <Box>
      {budget === null && <Alert severity="info" sx={{ mb: 1 }}>{t('No budget set for this project.')}</Alert>}
      {budget !== null && crossing >= 0 && (
        <Alert severity="warning" sx={{ mb: 1 }}>
          {t('The forecast goes over budget in the week of {date}.', { date: formatDate(series.weeks[crossing]) })}
        </Alert>
      )}
      {budget !== null && crossing < 0 && (
        <Alert severity="success" sx={{ mb: 1 }}>{t('The forecast stays within budget.')}</Alert>
      )}
      <LineChart
        height={280}
        series={lines}
        xAxis={[{ scaleType: 'point', data: labels }]}
        yAxis={[{ valueFormatter: (v) => formatMoney(v) }]}
        margin={{ left: 70, right: 16, top: 16, bottom: 30 }}
        sx={{
          '& .MuiLineElement-series-forecast, & path[data-series="forecast"]': { strokeDasharray: '6 4' },
          '& .MuiLineElement-series-budget, & path[data-series="budget"]': { strokeDasharray: '3 4' },
        }}
      />
    </Box>
  );
}

BudgetBurnChart.propTypes = {
  series: PropTypes.shape({
    weeks: PropTypes.arrayOf(PropTypes.string).isRequired,
    to_date: PropTypes.array.isRequired,
    forecast: PropTypes.array.isRequired,
    budget: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
  }).isRequired,
};
