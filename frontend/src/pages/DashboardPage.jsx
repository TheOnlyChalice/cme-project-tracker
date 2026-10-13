import {
  Box, Card, CardActionArea, CardContent, Paper, Stack, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Typography,
} from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import { api } from '../api/client.js';
import { useAuth } from '../auth/AuthContext.js';
import ErrorAlert from '../components/ErrorAlert.jsx';
import Loading from '../components/Loading.jsx';
import PageHeader from '../components/PageHeader.jsx';
import ProgressCell from '../components/ProgressCell.jsx';
import RiskFlags from '../components/RiskFlags.jsx';
import StatCard from '../components/StatCard.jsx';
import useIsMobile from '../hooks/useIsMobile.js';
import useLoader from '../hooks/useLoader.js';
import { useLanguage } from '../i18n/LanguageContext.js';
import { flagText } from '../i18n/translate.js';
import { formatDate, formatHours, formatMoney } from '../utils/format.js';
import { isManager } from '../utils/roles.js';

// [DASHBOARD HERE]
// How: Loads project health (/insights/projects) plus either team utilization
//      (managers and admins) or the user's own week (employees), then shows
//      headline numbers, the at-risk projects, and a health table.
// Why: Answers the business questions at a glance: project status, which
//      projects are at risk and why, how people are allocated, and budget
//      used versus planned. Each role sees only its own slice, because the
//      backend filters every answer.
/** Home page with project health, risks, and hours at a glance. */
export default function DashboardPage() {
  const { user } = useAuth();
  const { lang, t } = useLanguage();
  const manager = isManager(user);
  const isMobile = useIsMobile();

  const { data, loading, error, reload } = useLoader(async () => {
    const [projects, people] = await Promise.all([
      api('/insights/projects'),
      manager ? api('/insights/utilization') : api(`/users/${user.id}/availability`),
    ]);
    return { projects: projects.projects, people };
  }, [user.id, manager]);

  if (loading && !data) return <Loading label="Loading dashboard" />;
  if (error) return <ErrorAlert error={error} onRetry={reload} />;

  const { projects, people } = data;
  const atRisk = projects.filter((p) => p.at_risk);

  let peopleStat;
  if (manager) {
    const team = people.employees;
    const free = team.reduce((sum, row) => sum + Number(row.available), 0);
    const full = team.filter((row) => row.state === 'fully_booked').length;
    peopleStat = (
      <StatCard label={t('Team hours free this week')} value={formatHours(free)}
        caption={t('{full} of {total} people fully booked', { full, total: team.length })} />
    );
  } else {
    peopleStat = (
      <StatCard label={t('Your hours this week')} value={`${formatHours(people.assigned)} / 40`}
        caption={t('{hours} not yet assigned', { hours: formatHours(people.available) })} />
    );
  }

  const daysLeft = (p) => t('{days} days left', { days: p.days_left });

  return (
    <>
      <PageHeader title={t('Welcome, {name}', { name: user.first_name })} subtitle={t("Here's how your projects are doing.")} />

      <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', sm: 'repeat(3, 1fr)' }, mb: 3 }}>
        <StatCard label={t('Active projects')} value={projects.length} />
        <StatCard label={t('At risk')} value={atRisk.length} color={atRisk.length ? 'warning.main' : 'success.main'}
          caption={atRisk.length ? t('Need attention') : t('All on track')} />
        {peopleStat}
      </Box>

      {atRisk.length > 0 && (
        <>
          <Typography variant="h6" component="h2" sx={{ mb: 1 }}>{t('Needs attention')}</Typography>
          <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)' }, mb: 3 }}>
            {atRisk.map((project) => (
              <Card key={project.project_id} sx={{ borderColor: 'warning.main' }}>
                <CardActionArea component={RouterLink} to={`/projects/${project.project_id}`}>
                  <CardContent>
                    <Typography variant="subtitle1" fontWeight={600}>{project.name}</Typography>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      {t('Ends {date}', { date: formatDate(project.end_date) })} · {daysLeft(project)}
                    </Typography>
                    <Stack spacing={0.5}>
                      {project.risk_flags.map((flag) => (
                        <Typography key={flag.code} variant="body2">• {flagText(flag, lang)}</Typography>
                      ))}
                    </Stack>
                  </CardContent>
                </CardActionArea>
              </Card>
            ))}
          </Box>
        </>
      )}

      <Typography variant="h6" component="h2" sx={{ mb: 1 }}>{t('Project health')}</Typography>
      {projects.length === 0 && <Typography color="text.secondary">{t('No active projects to show.')}</Typography>}

      {isMobile ? (
        <Stack spacing={2}>
          {projects.map((p) => (
            <Card key={p.project_id}>
              <CardActionArea component={RouterLink} to={`/projects/${p.project_id}`}>
                <CardContent>
                  <Typography fontWeight={600}>{p.name}</Typography>
                  <Typography variant="body2" color="text.secondary" gutterBottom>{daysLeft(p)}</Typography>
                  <Stack spacing={1}>
                    <ProgressCell value={p.percent_complete}
                      label={t('Milestones {done}/{total}', { done: p.milestones_completed, total: p.milestones_total })} />
                    <ProgressCell value={p.percent_hours_assigned}
                      label={t('Hours {used} of {total}', { used: formatHours(p.hours_assigned), total: p.allocated_hours })} />
                    <RiskFlags flags={p.risk_flags} />
                  </Stack>
                </CardContent>
              </CardActionArea>
            </Card>
          ))}
        </Stack>
      ) : (
        projects.length > 0 && (
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
                      <Typography component={RouterLink} to={`/projects/${p.project_id}`} color="primary" sx={{ textDecoration: 'none', fontWeight: 600 }}>
                        {p.name}
                      </Typography>
                    </TableCell>
                    <TableCell>{formatDate(p.end_date)}<br /><Typography variant="caption" color="text.secondary">{daysLeft(p)}</Typography></TableCell>
                    <TableCell>
                      <ProgressCell value={p.percent_complete}
                        label={t('{done} of {total}', { done: p.milestones_completed, total: p.milestones_total })} />
                    </TableCell>
                    <TableCell>
                      <ProgressCell value={p.percent_hours_assigned}
                        label={t('{used} of {total} h', { used: formatHours(p.hours_assigned), total: p.allocated_hours })} />
                    </TableCell>
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
        )
      )}
    </>
  );
}
