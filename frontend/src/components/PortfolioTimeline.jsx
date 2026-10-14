import { Box, ButtonBase, Chip, Link, ToggleButton, ToggleButtonGroup, Tooltip, Typography } from '@mui/material';
import PropTypes from 'prop-types';
import { useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import useIsMobile from '../hooks/useIsMobile.js';
import { useT } from '../i18n/LanguageContext.js';
import { formatDate, getFormatLocale, toIsoDate } from '../utils/format.js';

const DAY = 86400000;
const toTime = (iso) => Date.parse(`${iso}T00:00:00Z`);
const STATE_LABELS = { done: 'Completed', in_progress: 'In progress', planned: 'Planned', overdue: 'Overdue' };

function windowFor(zoom) {
  const now = new Date();
  const back = zoom === 'quarters' ? 3 : 1;
  const months = zoom === 'quarters' ? 12 : 6;
  const start = new Date(Date.UTC(now.getFullYear(), now.getMonth() - back, 1));
  const end = new Date(Date.UTC(now.getFullYear(), now.getMonth() - back + months, 1));
  return { start: start.getTime(), end: end.getTime(), months };
}

// Colors for each milestone state, read from the theme's brand palette.
function barSx(state) {
  const base = { borderRadius: 2, border: '1.5px solid transparent' };
  if (state === 'done') return { ...base, bgcolor: 'brand.barDone', color: 'brand.barDoneText' };
  if (state === 'in_progress') return { ...base, bgcolor: 'brand.barActive', color: 'brand.barActiveText' };
  if (state === 'overdue') {
    return {
      ...base, bgcolor: 'brand.accent', color: 'brand.accentText',
      backgroundImage: 'repeating-linear-gradient(135deg, rgba(8,26,56,0.18) 0 6px, transparent 6px 12px)',
    };
  }
  return { ...base, bgcolor: 'background.paper', color: 'text.primary', borderColor: 'brand.barPlannedBorder' };
}

// [ACME: PORTFOLIO TIMELINE HERE]
// How: Draws each project as a horizontal lane with its milestones as bars
//      across the months: completed (muted), in progress (solid), planned
//      (outlined), and overdue (amber with stripes). An amber line marks
//      today, the lane label shows the manager and a risk badge, and the
//      Months / Quarters switch zooms between 6 and 12 months. Hover a bar
//      for its name, dates, and state.
// Why: The signature view of the app. It answers "what's happening when,
//      and what's slipping?" in one glance, shows the milestone dependency
//      chain visually, and makes the date-shifting feature easy to see.
/** Gantt-style lanes of milestone bars with a today marker. */
export default function PortfolioTimeline({ lanes, title, actions, linkLanes = true, onBarClick }) {
  const t = useT();
  const isMobile = useIsMobile();
  const [zoom, setZoom] = useState('months');
  const range = windowFor(zoom);
  const span = range.end - range.start;
  const pct = (time) => Math.max(0, Math.min(100, ((time - range.start) / span) * 100));
  const todayIso = toIsoDate(new Date());
  const todayLeft = pct(toTime(todayIso));
  const labelWidth = isMobile ? 140 : 236;

  const monthMarks = [];
  for (let i = 0; i < range.months; i += 1) {
    const at = new Date(range.start);
    at.setUTCMonth(at.getUTCMonth() + i);
    const label = at.toLocaleDateString(getFormatLocale(), { month: 'short', timeZone: 'UTC', ...(at.getUTCMonth() === 0 ? { year: 'numeric' } : {}) });
    monthMarks.push({ left: pct(at.getTime()), label, key: at.toISOString() });
  }

  const legend = [['done', t('Completed')], ['in_progress', t('In progress')], ['planned', t('Planned')], ['overdue', t('Overdue')]];

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 2 }}>
        {title && <Typography variant="h6" component="h2" sx={{ flexGrow: 1 }}>{title}</Typography>}
        {actions}
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1.75 }} aria-label={t('Legend')}>
          {legend.map(([state, label]) => (
            <Box key={state} sx={{ display: 'flex', alignItems: 'center', gap: 0.75, fontSize: 13, color: 'text.secondary' }}>
              <Box sx={{ ...barSx(state), width: 16, height: 10, borderRadius: 0.75 }} />
              {label}
            </Box>
          ))}
        </Box>
        <ToggleButtonGroup size="small" exclusive value={zoom} onChange={(_, next) => next && setZoom(next)} aria-label={t('Zoom')}>
          <ToggleButton value="months" sx={{ px: 1.5 }}>{t('Months')}</ToggleButton>
          <ToggleButton value="quarters" sx={{ px: 1.5 }}>{t('Quarters')}</ToggleButton>
        </ToggleButtonGroup>
      </Box>

      <Box sx={{ overflowX: 'auto' }}>
        <Box sx={{ minWidth: 760 }}>
          <Box sx={{ display: 'flex' }}>
            <Box sx={{ flex: `0 0 ${labelWidth}px` }} />
            <Box sx={{ flexGrow: 1, position: 'relative', height: 30, borderBottom: 1, borderColor: 'divider' }}>
              {monthMarks.map((m) => (
                <Typography key={m.key} variant="body2" sx={{ position: 'absolute', left: `${m.left}%`, top: 4, pl: 1, fontWeight: 600, color: 'text.secondary' }}>
                  {m.label}
                </Typography>
              ))}
              <Box sx={{
                position: 'absolute', left: `${todayLeft}%`, top: 2, transform: 'translateX(-50%)',
                bgcolor: 'brand.accent', color: 'brand.accentText', fontSize: 11, fontWeight: 700, px: 1, py: 0.25, borderRadius: 999,
              }}>
                {t('Today')}
              </Box>
            </Box>
          </Box>

          {lanes.length === 0 && (
            <Typography color="text.secondary" sx={{ py: 3 }}>{t('No active projects to show.')}</Typography>
          )}

          {lanes.map((lane) => (
            <Box key={lane.id} sx={{ display: 'flex', borderBottom: 1, borderColor: 'divider' }}>
              <Box sx={{ flex: `0 0 ${labelWidth}px`, py: 1.75, pr: 2, display: 'flex', flexDirection: 'column', gap: 0.5, minWidth: 0 }}>
                {linkLanes ? (
                  <Link component={RouterLink} to={`/projects/${lane.id}`} underline="hover" noWrap sx={{ fontWeight: 600 }}>{lane.name}</Link>
                ) : (
                  <Typography noWrap sx={{ fontWeight: 600 }}>{lane.name}</Typography>
                )}
                <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 0.75 }}>
                  {lane.subtitle && <Typography variant="caption" color="text.secondary" noWrap>{lane.subtitle}</Typography>}
                  {lane.badge && (
                    <Chip size="small" label={lane.badge} color={lane.risk ? 'warning' : 'default'}
                      variant={lane.risk ? 'filled' : 'outlined'} sx={{ height: 20, fontSize: 11 }} />
                  )}
                </Box>
              </Box>
              <Box sx={{ flexGrow: 1, position: 'relative', minHeight: 64 }}>
                {monthMarks.slice(1).map((m) => (
                  <Box key={m.key} sx={{ position: 'absolute', top: 0, bottom: 0, left: `${m.left}%`, borderLeft: '1px dashed', borderColor: 'brand.gridLine' }} />
                ))}
                <Box sx={{ position: 'absolute', top: 0, bottom: 0, left: `${todayLeft}%`, borderLeft: 2, borderColor: 'brand.accent' }} />
                {lane.bars.length === 0 && lane.start && (
                  <Box sx={{
                    position: 'absolute', top: 18, height: 28, left: `${pct(toTime(lane.start))}%`,
                    width: `${Math.max(pct(toTime(lane.end) + DAY) - pct(toTime(lane.start)), 1)}%`,
                    border: '1.5px dashed', borderColor: 'text.secondary', borderRadius: 2, display: 'flex', alignItems: 'center',
                    px: 1.25, fontSize: 12, color: 'text.secondary', overflow: 'hidden', whiteSpace: 'nowrap', boxSizing: 'border-box',
                  }}>
                    {t('No milestones yet')}
                  </Box>
                )}
                {lane.bars.map((bar) => {
                  const left = pct(toTime(bar.start));
                  const right = pct(toTime(bar.end) + DAY);
                  if (right <= 0 || left >= 100) return null;
                  return (
                    <Tooltip key={bar.id} title={`${bar.label} · ${formatDate(bar.start)} – ${formatDate(bar.end)} · ${t(STATE_LABELS[bar.state])}`}>
                      {/* [ACME: CLICKABLE TIMELINE BARS HERE]
                          How: Each bar is a button: clicking it (or Enter) opens
                               that milestone on its project page.
                          Why: Seeing a slipping milestone and getting to it should
                               be one click, not a search. */}
                      <ButtonBase
                        onClick={onBarClick ? () => onBarClick(lane.id, bar.id) : undefined}
                        tabIndex={0}
                        aria-label={`${bar.label}, ${formatDate(bar.start)} – ${formatDate(bar.end)}, ${t(STATE_LABELS[bar.state])}`}
                        sx={{
                          justifyContent: 'flex-start', cursor: onBarClick ? 'pointer' : 'default',
                          ...barSx(bar.state), position: 'absolute', top: 18, height: 28, left: `${left}%`,
                          width: `${Math.max(right - left - 0.3, 0.6)}%`, boxSizing: 'border-box', display: 'flex', alignItems: 'center',
                          px: 1.25, fontSize: 12, fontWeight: 600, overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis',
                          transition: (theme) => theme.transitions.create(['left', 'width']),
                          outline: bar.current ? '2px solid' : 'none', outlineColor: 'brand.accent', outlineOffset: 2,
                          '&:hover, &:focus-visible': { filter: 'brightness(1.08)' },
                        }}
                      >
                        <Box component="span" sx={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{bar.label}</Box>
                      </ButtonBase>
                    </Tooltip>
                  );
                })}
              </Box>
            </Box>
          ))}
        </Box>
      </Box>
    </Box>
  );
}

PortfolioTimeline.propTypes = {
  lanes: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.string.isRequired,
    name: PropTypes.string.isRequired,
    subtitle: PropTypes.string,
    badge: PropTypes.string,
    risk: PropTypes.bool,
    start: PropTypes.string,
    end: PropTypes.string,
    bars: PropTypes.arrayOf(PropTypes.shape({
      id: PropTypes.string.isRequired,
      label: PropTypes.string.isRequired,
      start: PropTypes.string.isRequired,
      end: PropTypes.string.isRequired,
      state: PropTypes.oneOf(['done', 'in_progress', 'planned', 'overdue']).isRequired,
      current: PropTypes.bool,
    })).isRequired,
  })).isRequired,
  title: PropTypes.node,
  actions: PropTypes.node,
  linkLanes: PropTypes.bool,
  onBarClick: PropTypes.func,
};
