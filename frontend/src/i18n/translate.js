import es from './es.js';

const DICTIONARIES = { es };

// [ACME: TRANSLATION LOOKUP HERE]
// How: The English sentence itself is the key. Spanish comes from es.js; if
//      a sentence is missing there, the English is shown instead. {name}
//      placeholders are filled in after translating.
// Why: Code stays readable (t('Sign in') rather than t('auth.btn.signIn')),
//      and a missing translation can never break the page or show a blank.
export function translate(lang, text, vars) {
  const template = (lang !== 'en' && DICTIONARIES[lang]?.[text]) || text;
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (match, key) => (key in vars ? String(vars[key]) : match));
}

// [ACME: ERROR TRANSLATION HERE]
// How: Backend errors are matched by their code (e.g. "account_locked") and
//      rebuilt in the chosen language using numbers from error.details.
//      Unknown codes fall back to the backend's English message.
// Why: The backend speaks English; its error codes and details let the
//      frontend show the same message in Spanish without the backend needing
//      to know the user's language.
const ERROR_TEMPLATES = {
  invalid_credentials: 'The username or password is incorrect.',
  account_locked: 'Too many failed attempts. Try again in {minutes} minutes.',
  token_expired: 'Your session has expired. Please sign in again.',
  token_revoked: "You've been signed out. Please sign in again.",
  invalid_token: 'Your session is no longer valid. Please sign in again.',
  invalid_user: 'This account no longer exists or is archived.',
  authentication_required: 'Please sign in.',
  forbidden: "You don't have permission to do this.",
  not_found: 'Not found. It may have been archived, or you may not have access.',
  network_error: 'Could not reach the server. Check your connection.',
  storage_unavailable: 'The database is waking up. Try again in a moment.',
  internal_error: 'Something went wrong on the server.',
  validation_error: 'Some fields are invalid.',
  unknown_fields: "Some of these fields can't be changed here.",
  no_changes: 'Nothing to save.',
  email_taken: 'Another user already has this email.',
  name_taken: 'Another project already has this name.',
  conflict: 'That conflicts with an existing record.',
  weekly_capacity_exceeded: 'This employee only has {hours} hours left that week.',
  project_hours_exceeded: 'This project only has {hours} allocated hours left.',
  already_assigned: 'This employee already has hours on this milestone that week. Change that booking instead.',
  week_closed: "That week has ended and can't be changed.",
  milestone_closed: 'Hours can only go to active milestones.',
  project_closed: 'This project is completed, abandoned, or archived. Restore it first.',
  milestones_outside_dates: 'Some milestones would fall outside the new dates.',
  milestones_past_project_end: "The moved milestones would end {days} days after the project. Tick 'extend the project end date' or choose other dates.",
  milestones_before_project_start: 'Some milestones would start before the project does.',
  hours_outside_dates: 'Hours are booked for weeks outside the new dates. Remove those hours first.',
  below_assigned_hours: 'Allocated hours cannot be lower than the hours already assigned.',
  has_reports: "Reassign this person's team before doing this.",
  manages_projects: "Reassign this person's active projects first.",
  last_admin: "You can't remove the last admin.",
  manager_required: 'Employees must have a manager.',
  self_archive: "You can't archive yourself.",
  archived: 'Restore this person before editing them.',
  manager_archived: 'Their manager is archived. Restore the manager first.',
  already_archived: 'This is already archived.',
  not_archived: "This isn't archived.",
  milestone_completed: "Completed milestones can't be edited.",
  milestone_archived: 'Restore this milestone first.',
  already_completed: 'This milestone is already completed.',
};

// [ACME: ERROR STATUS CODE HERE]
// How: Every error from the server is labeled with its HTTP status code,
//      e.g. "Error 400" (invalid input), 401 (signed out), 403 (not allowed),
//      404 (not found), 409 (conflicts with the rules), 429 (locked out),
//      500 or 503 (server problems). Connection failures say "Network error".
// Why: Your request: the code tells people (and support staff) at a glance
//      what kind of problem it is, alongside the plain-language message.
export function errorStatus(error, lang) {
  if (!error || error.status === undefined || error.status === null) return '';
  if (error.status === 0) return translate(lang, 'Network error');
  return translate(lang, 'Error {status}', { status: error.status });
}

export function errorText(error, lang) {
  if (!error) return '';
  const template = ERROR_TEMPLATES[error.code];
  if (lang === 'en' || !template) return error.message || translate(lang, 'Something went wrong.');
  const details = error.details || {};
  return translate(lang, template, { minutes: details.minutes, hours: details.hours_remaining, days: details.days_over });
}

/** Translate one per-field validation message from the backend. */
export const detailText = (message, lang) => translate(lang, message);

// [ACME: RISK FLAG TRANSLATION HERE]
// How: Each risk flag carries a code and its numbers (params); the sentence
//      is rebuilt from a template in the chosen language.
// Why: Flags are shown on every dashboard, so they must read naturally in
//      both languages, with the right numbers in the right places.
const FLAG_TEMPLATES = {
  past_end_date: 'The project ended {days} days ago but is still active.',
  overdue_milestone: 'Overdue milestones: {names}.',
  deadline_near: '{days} days left with {open} milestones open.',
  behind_schedule: '{elapsed}% of the time has passed but only {complete}% of milestones are complete.',
  no_milestones: 'The project has started but has no milestones.',
  over_budget: 'Forecast labor cost exceeds the budget.',
  over_budget_amounts: 'Committed labor cost {cost} exceeds the budget {budget}.',
  hours_nearly_used: '{percent}% of allocated hours are assigned.',
  inactive: 'No activity for {days} days.',
};

export const FLAG_LABELS = {
  past_end_date: 'Past end date',
  overdue_milestone: 'Overdue milestone',
  deadline_near: 'Deadline near',
  behind_schedule: 'Behind schedule',
  no_milestones: 'No milestones',
  over_budget: 'Over budget',
  hours_nearly_used: 'Hours nearly used',
  inactive: 'Inactive',
};

export function flagText(flag, lang) {
  const params = flag.params || {};
  const code = flag.code === 'over_budget' && params.cost !== undefined ? 'over_budget_amounts' : flag.code;
  const template = FLAG_TEMPLATES[code];
  if (lang === 'en' || !template) return flag.message;
  return translate(lang, template, params);
}
