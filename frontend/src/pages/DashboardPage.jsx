import WarningAmberIcon from '@mui/icons-material/WarningAmberRounded';
import {
  Box, Button, Card, CardActionArea, CardContent, LinearProgress, Link, Paper, Stack, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Typography,
} from '@mui/material';
import PropTypes from 'prop-types';
import { Link as RouterLink } from 'react-router-dom';
import { api } from '../api/client.js';
import { useAuth } from '../auth/AuthContext.js';
import ErrorAlert from '../components/ErrorAlert.jsx';
import Loading from '../components/Loading.jsx';
import PortfolioTimeline from '../components/PortfolioTimeline.jsx';
import ProgressCell from '../components/ProgressCell.jsx';
import RiskFlags from '../components/RiskFlags.jsx';
import useIsMobile from '../hooks/useIsMobile.js';
import useLoader from '../hooks/useLoader.js';
import { useLanguage } from '../i18n/LanguageContext.js';
import { FLAG_LABELS, flagText } from '../i18n/translate.js';
import { addDays, formatDate, formatHours, formatMoney, getFormatLocale, toIsoDate } from '../utils/format.js';
import { isManager } from '../utils/roles.js';

/** One headline number inside the navy banner. */
function BannerStat({ label, value, caption, highlight }) {
  return (
    <Box sx={{ bgcolor: 'rgba(255,255,255,0.08)', borderRadius: 3.5, p: 2.25, display: 'flex', flexDirection: 'column', gap: 0.5, minWidth: 0 }}>
      <Typography variant="body2" sx={{ color: 'brand.sidebarMuted' }}>{label}</Typography>
      <Typography variant="h4" component="p" sx={{ color: highlight ? 'brand.accent' : '#ffffff' }}>{value}</Typography>
      {caption && <Typography variant="body2" noWrap sx={{ color: 'brand.sidebarMuted' }}>{caption}</Typography>}
    </Box>
  );
}

BannerStat.propTypes = {
  label: PropTypes.node.isRequired,
  value: PropTypes.node,
  caption: PropTypes.node,
  highlight: PropTypes.bool,
};

// [DASHBOARD HERE]
// How: A navy welcome banner with today's date and four headline numbers,
//      then the portfolio timeline, then two cards ("Needs attention" with
//      each risk's reason, and this week's capacity), and finally the
//      project health table with milestones, hours, and budget. Employees
//      see their own hours instead of the team's, and no budget figures.
// Why: Answers the business questions in order of urgency: what's at risk,
//      what's happening when, who has room, and how budgets are tracking.
//      Every number comes from the backend, which only returns what the
//      user's role may see.
/** Home page: banner, portfolio timeline, risks, capacity, and project health. */
export default function DashboardPage() {
  const { user } = useAuth();
  const { lang, t } = useLanguage();
  const manager = isManager(user);
  const isMobile = useIsMobile();

  const { data, loading, error, reload } = useLoader(async () => {
    const [health, timeline, people] = await Promise.all([
      api('/insights/projects'),
      api('/insights/timeline'),
      manager ? api('/insights/utilization') : api(`/users/${user.id}/availability`),
    ]);
    return { projects: health.projects, timeline: timeline.projects, people };
  }, [user.id, manager]);

  if (loading && !data) return <Loading label="Loading dashboard" />;
  if (error) return <ErrorAlert error={error} onRetry={reload} />;

  const { projects, timeline, people } = data;
  const atRisk = projects.filter((p) => p.at_risk);
  const today = toIsoDate(new Date());
  const in30 = addDays(today, 30);
  const due = timeline.flatMap((lane) => lane.milestones)
    .filter((m) => m.state !== 'done' && m.end_date >= today && m.end_date <= in30)
    .sort((a, b) => a.end_date.localeCompare(b.end_date));
  const managers = new Set(timeline.map((lane) => lane.manager_name)).size;
  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning, {name}' : hour < 18 ? 'Good afternoon, {name}' : 'Good evening, {name}';

  const lanes = timeline.map((lane) => ({
    id: lane.project_id,
    name: lane.name,
    subtitle: lane.manager_name,
    risk: lane.at_risk,
    badge: lane.at_risk ? t(FLAG_LABELS[lane.risk_flags[0]?.code] || 'At risk') : t('On track'),
    start: lane.start_date,
    end: lane.end_date,
    bars: lane.milestones.map((m) => ({ id: m.id, label: m.name, start: m.start_date, end: m.end_date, state: m.state })),
  }));

  let hoursStat;
  if (manager) {
    const team = people.employees;
    const free = team.reduce((sum, row) => sum + Number(row.available), 0);
    const full = team.filter((row) => row.state === 'fully_booked').length;
    hoursStat = (
      <BannerStat label={t('Free hours this week')} value={formatHours(free)}
        caption={t('of {total} h · {full} people full', { total: team.length * 40, full })} />
    );
  } else {
    hoursStat = (
      <BannerStat label={t('Your hours this week')} value={`${formatHours(people.assigned)} / 40`}
        caption={t('{hours} not yet assigned', { hours: formatHours(people.available) })} />
    );
  }

  const capacityRows = manager
    ? [...people.employees].sort((a, b) => Number(b.assigned) - Number(a.assigned))
      .map((row) => ({ key: row.user_id, label: row.name, hours: Number(row.assigned) }))
    : people.assignments.map((a) => ({ key: a.assignment_id, label: `${a.project_name} · ${a.milestone_name}`, hours: Number(a.hours) }));

  return (
    <Stack spacing={3}>
      {/* [WELCOME BANNER HERE]
          How: A solid navy panel with today's date, a time-of-day greeting,
               an amber shortcut to the at-risk list, and four headline numbers.
          Why: The first thing anyone sees sums up the state of their world
               in ACME's colors, with the most urgent action one click away. */}
      <Box component="section" aria-label={t('Overview')}
        sx={{ bgcolor: 'brand.banner', color: '#ffffff', borderRadius: 4.5, p: { xs: 2.5, md: 3.5 }, display: 'flex', flexDirection: 'column', gap: 2.75 }}>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'flex-end', justifyContent: 'space-between', gap: 1.5 }}>
          <Box>
            <Typography variant="body2" sx={{ color: 'brand.sidebarMuted', mb: 0.5 }}>
              {new Date().toLocaleDateString(getFormatLocale(), { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}
            </Typography>
            <Typography variant="h4" component="h1">{t(greeting, { name: user.first_name })}</Typography>
          </Box>
          {atRisk.length > 0 && (
            <Button variant="contained" color="secondary" startIcon={<WarningAmberIcon />} sx={{ minHeight: 44, px: 2.25 }}
              onClick={() => document.getElementById('attention')?.scrollIntoView({ behavior: 'smooth', block: 'start' })}>
              {t('Review {count} at-risk projects', { count: atRisk.length })}
            </Button>
          )}
        </Box>
        <Box sx={{ display: 'grid', gap: 1.75, gridTemplateColumns: { xs: 'repeat(2, minmax(0, 1fr))', lg: 'repeat(4, minmax(0, 1fr))' } }}>
          <BannerStat label={t('Active projects')} value={projects.length}
            caption={manager ? t('across {count} managers', { count: managers }) : t("on your manager's team")} />
          <BannerStat label={t('At risk')} value={atRisk.length} highlight={atRisk.length > 0}
            caption={atRisk.length ? t('Need attention') : t('All on track')} />
          {hoursStat}
          <BannerStat label={t('Milestones due in 30 days')} value={due.length}
            caption={due.length ? t('next: {date}', { date: formatDate(due[0].end_date) }) : t('nothing due soon')} />
        </Box>
      </Box>

      <Card>
        <CardContent>
          <PortfolioTimeline title={t('Portfolio timeline')} lanes={lanes} />
        </CardContent>
      </Card>

      <Box sx={{ display: 'grid', gap: 3, gridTemplateColumns: { xs: '1fr', md: 'repeat(2, minmax(0, 1fr))' } }}>
        <Card id="attention" component="section" aria-label={t('Needs attention')}>
          <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
            <Typography variant="h6" component="h2">{t('Needs attention')}</Typography>
            {atRisk.length === 0 && <Typography color="text.secondary">{t('All on track')}</Typography>}
            {atRisk.map((project) => (
              <CardActionArea key={project.project_id} component={RouterLink} to={`/projects/${project.project_id}`}
                sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'flex-start', gap: 1.75, p: 1.75, borderRadius: 3, bgcolor: 'action.hover' }}>
                <Box aria-hidden="true" sx={{ flex: '0 0 40px', height: 40, borderRadius: 2.5, bgcolor: 'warning.main', color: 'warning.contrastText', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <WarningAmberIcon />
                </Box>
                <Box sx={{ minWidth: 0 }}>
                  <Typography sx={{ fontWeight: 600 }}>{project.name}</Typography>
                  {project.risk_flags.map((flag) => (
                    <Typography key={flag.code} variant="body2" color="text.secondary">{flagText(flag, lang)}</Typography>
                  ))}
                </Box>
              </CardActionArea>
            ))}
          </CardContent>
        </Card>

        <Card component="section" aria-label={manager ? t('Team capacity this week') : t('Your week')}>
          <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
            <Box sx={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 1 }}>
              <Typography variant="h6" component="h2">{manager ? t('Team capacity this week') : t('Your week')}</Typography>
              <Link component={RouterLink} to="/hours" sx={{ fontWeight: 600, fontSize: 14 }}>{manager ? t('Open heat map') : t('Open my week')}</Link>
            </Box>
            {capacityRows.length === 0 && <Typography color="text.secondary">{t('Nothing booked this week.')}</Typography>}
            {capacityRows.map((row) => (
              <Box key={row.key} sx={{ display: 'grid', gridTemplateColumns: 'minmax(0, 150px) minmax(0, 1fr) 56px', alignItems: 'center', gap: 1.5 }}>
                <Typography variant="body2" noWrap>{row.label}</Typography>
                <LinearProgress variant="determinate" value={Math.min((row.hours / 40) * 100, 100)}
                  color={row.hours >= 40 ? 'secondary' : 'primary'} sx={{ height: 10 }} aria-label={row.label} />
                <Typography variant="body2" sx={{ textAlign: 'right', fontWeight: 600 }}>{formatHours(row.hours)}</Typography>
              </Box>
            ))}
          </CardContent>
        </Card>
      </Box>

      <Box component="section" aria-label={t('Project health')}>
        <Typography variant="h6" component="h2" sx={{ mb: 1.5 }}>{t('Project health')}</Typography>
        {projects.length === 0 && <Typography color="text.secondary">{t('No active projects to show.')}</Typography>}
        {isMobile ? (
          <Stack spacing={2}>
            {projects.map((p) => (
              <Card key={p.project_id}>
                <CardActionArea component={RouterLink} to={`/projects/${p.project_id}`}>
                  <CardContent>
                    <Typography sx={{ fontWeight: 600 }}>{p.name}</Typography>
                    <Typography variant="body2" color="text.secondary" gutterBottom>{t('{days} days left', { days: p.days_left })}</Typography>
                    <Stack spacing={1}>
                      <ProgressCell value={p.percent_complete} label={t('Milestones {done}/{total}', { done: p.milestones_completed, total: p.milestones_total })} />
                      <ProgressCell value={p.percent_hours_assigned} label={t('Hours {used} of {total}', { used: formatHours(p.hours_assigned), total: p.allocated_hours })} />
                      <RiskFlags flags={p.risk_flags} />
                    </Stack>
                  </CardContent>
                </CardActionArea>
              </Card>
            ))}
          </Stack>
        ) : projects.length > 0 && (
          <TableContainer component={Paper} variant="outlined">
            <Table size="small" aria-label={t('Project health')}>
              <TableHead>
                <TableRow>
                  <TableCell>{t('Project')}</TableCell>
                  <TableCell>{t('Ends')}</TableCell>
                  <TableCell>{t('Milestones')}</TableCell>
                  <TableCell>{t('Hours assigned')}</TableCell>
                  {manager && <TableCell>{t('Budget used')}</TableCell>}
                  <TableCell>{t('Risk')}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {projects.map((p) => (
                  <TableRow key={p.project_id} hover>
                    <TableCell>
                      <Link component={RouterLink} to={`/projects/${p.project_id}`} underline="hover" sx={{ fontWeight: 600 }}>{p.name}</Link>
                    </TableCell>
                    <TableCell>
                      {formatDate(p.end_date)}<br />
                      <Typography variant="caption" color="text.secondary">{t('{days} days left', { days: p.days_left })}</Typography>
                    </TableCell>
                    <TableCell><ProgressCell value={p.percent_complete} label={t('{done} of {total}', { done: p.milestones_completed, total: p.milestones_total })} /></TableCell>
                    <TableCell><ProgressCell value={p.percent_hours_assigned} label={t('{used} of {total} h', { used: formatHours(p.hours_assigned), total: p.allocated_hours })} /></TableCell>
                    {manager && (
                      <TableCell>
                        <ProgressCell value={p.percent_budget_used}
                          label={p.budget ? t('{used} of {total}', { used: formatMoney(p.labor_cost_to_date), total: formatMoney(p.budget) }) : t('No budget')} />
                      </TableCell>
                    )}
                    <TableCell><RiskFlags flags={p.risk_flags} /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Box>
    </Stack>
  );
}
