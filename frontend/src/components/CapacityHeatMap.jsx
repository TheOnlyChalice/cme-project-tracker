import { Box, ButtonBase, Link, Tooltip, Typography } from '@mui/material';
import PropTypes from 'prop-types';
import { Link as RouterLink } from 'react-router-dom';
import { useT } from '../i18n/LanguageContext.js';
import { formatDate, formatHours } from '../utils/format.js';

// Which shade a week gets: 0 h, under 20, under 35, under 40, full.
function bucket(hours) {
  const h = Number(hours);
  if (h >= 40) return 4;
  if (h >= 35) return 3;
  if (h >= 20) return 2;
  if (h > 0) return 1;
  return 0;
}

// [ACME: CAPACITY HEAT MAP HERE]
// How: One row per person and one column per week. Each cell is shaded by
//      how much of that person's 40 hours is booked (empty, light, medium,
//      nearly full, and amber when full) and shows the hours. The current
//      week has an amber outline; clicking any cell selects that week so the
//      bookings below switch to it.
// Why: Answers "who is over- or under-booked, and when?" across several
//      weeks at once, which a single-week list can't show, and turns the
//      40-hour rule into something visible.
/** People-by-week grid of booked hours. */
export default function CapacityHeatMap({ weeks, people, currentWeek, selectedWeek, onSelectWeek, linkPeople = false }) {
  const t = useT();
  const textFor = (level) => (level >= 3 ? (level === 4 ? 'brand.accentText' : 'common.white') : 'text.primary');
  const legend = [[0, t('Free')], [1, '1–19 h'], [2, '20–34 h'], [3, '35–39 h'], [4, t('Full (40 h)')]];
  const columns = `minmax(150px, 1.4fr) repeat(${weeks.length}, minmax(76px, 1fr))`;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
      <Box sx={{ overflowX: 'auto' }}>
        <Box role="table" aria-label={t('Booked hours by person and week')} sx={{ minWidth: 640, display: 'grid', gridTemplateColumns: columns, gap: 0.75 }}>
          <Box role="columnheader" />
          {weeks.map((week) => (
            <Box key={week} role="columnheader" sx={{
              textAlign: 'center', fontSize: 13, fontWeight: 600, py: 0.75, borderRadius: 1.5,
              color: week === selectedWeek ? 'primary.contrastText' : 'text.secondary',
              bgcolor: week === selectedWeek ? 'primary.main' : 'transparent',
            }}>
              {formatDate(week).replace(/,? \d{4}$/, '')}
            </Box>
          ))}
          {people.map((person) => (
            <Box key={person.user_id} role="row" sx={{ display: 'contents' }}>
              <Typography role="rowheader" noWrap sx={{ alignSelf: 'center', fontWeight: 500, pr: 1 }}>
                {linkPeople
                  ? <Link component={RouterLink} to={`/people/${person.user_id}`} underline="hover" color="inherit">{person.name}</Link>
                  : person.name}
              </Typography>
              {person.weeks.map((cell) => {
                const level = bucket(cell.hours);
                return (
                  <Tooltip key={cell.week_start}
                    title={t('{name}: {hours} of 40 h, week of {date}', { name: person.name, hours: formatHours(cell.hours), date: formatDate(cell.week_start) })}>
                    <ButtonBase
                      role="cell"
                      onClick={() => onSelectWeek(cell.week_start)}
                      aria-label={t('{name}: {hours} of 40 h, week of {date}', { name: person.name, hours: formatHours(cell.hours), date: formatDate(cell.week_start) })}
                      sx={(theme) => ({
                        height: 44, borderRadius: 2, fontSize: 13, fontWeight: 600,
                        bgcolor: theme.palette.brand.heat[level], color: textFor(level),
                        outline: cell.week_start === currentWeek ? `2px solid ${theme.palette.brand.accent}` : 'none',
                        outlineOffset: 1,
                        transition: theme.transitions.create(['transform', 'box-shadow']),
                        '&:hover, &:focus-visible': { transform: 'translateY(-1px)', boxShadow: '0 2px 8px rgba(8,26,56,0.18)' },
                      })}
                    >
                      {Number(cell.hours) ? formatHours(cell.hours) : '—'}
                    </ButtonBase>
                  </Tooltip>
                );
              })}
            </Box>
          ))}
        </Box>
      </Box>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 2, fontSize: 13, color: 'text.secondary' }}>
        {legend.map(([level, label]) => (
          <Box key={level} sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
            <Box sx={(theme) => ({ width: 16, height: 12, borderRadius: 0.75, bgcolor: theme.palette.brand.heat[level], border: 1, borderColor: 'divider' })} />
            {label}
          </Box>
        ))}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
          <Box sx={{ width: 16, height: 12, borderRadius: 0.75, outline: '2px solid', outlineColor: 'brand.accent' }} />
          {t('This week')}
        </Box>
      </Box>
    </Box>
  );
}

CapacityHeatMap.propTypes = {
  weeks: PropTypes.arrayOf(PropTypes.string).isRequired,
  people: PropTypes.arrayOf(PropTypes.shape({
    user_id: PropTypes.string.isRequired,
    name: PropTypes.string.isRequired,
    weeks: PropTypes.arrayOf(PropTypes.shape({ week_start: PropTypes.string, hours: PropTypes.oneOfType([PropTypes.number, PropTypes.string]) })).isRequired,
  })).isRequired,
  currentWeek: PropTypes.string,
  selectedWeek: PropTypes.string,
  onSelectWeek: PropTypes.func.isRequired,
  linkPeople: PropTypes.bool,
};
