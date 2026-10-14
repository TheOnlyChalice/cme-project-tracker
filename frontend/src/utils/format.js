// Shared display helpers so dates, money, and hours look the same everywhere.

let locale = 'en-US';

/** Set the language used for dates and numbers (called by LanguageProvider). */
export function setFormatLocale(next) {
  locale = next;
}

/** The language currently used for dates and numbers. */
export const getFormatLocale = () => locale;

export function formatDate(value) {
  if (!value) return '—';
  const [year, month, day] = String(value).slice(0, 10).split('-').map(Number);
  return new Date(year, month - 1, day).toLocaleDateString(locale, {
    month: 'short', day: 'numeric', year: 'numeric',
  });
}

export function formatDateTime(value) {
  if (!value) return '—';
  return new Date(value).toLocaleString(locale, {
    month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit',
  });
}

export function formatMoney(value) {
  if (value === null || value === undefined) return '—';
  return Number(value).toLocaleString(locale, { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });
}

export function formatHours(value) {
  if (value === null || value === undefined) return '—';
  const number = Number(value);
  return `${Number.isInteger(number) ? number : number.toFixed(1)} h`;
}

export const fullName = (user) => (user ? `${user.first_name} ${user.last_name}` : '—');

// [WEEK HELPERS HERE]
// How: Weeks are identified by their Monday as a YYYY-MM-DD string, matching
//      the backend's week_start.
// Why: Hours reset every Monday, so the week picker and every hours request
//      use the same Monday-based week the backend uses.
export function mondayOf(date = new Date()) {
  const copy = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const shift = (copy.getDay() + 6) % 7;
  copy.setDate(copy.getDate() - shift);
  return toIsoDate(copy);
}

export function addWeeks(isoMonday, weeks) {
  const [year, month, day] = isoMonday.split('-').map(Number);
  return toIsoDate(new Date(year, month - 1, day + weeks * 7));
}

export function toIsoDate(date) {
  const pad = (n) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

/** Move a YYYY-MM-DD date by a number of days. */
export function addDays(isoDay, days) {
  const [year, month, day] = isoDay.split('-').map(Number);
  return toIsoDate(new Date(year, month - 1, day + days));
}

/** Days from one YYYY-MM-DD date to another (negative if earlier). */
export function daysBetween(fromIso, toIso) {
  const [y1, m1, d1] = fromIso.split('-').map(Number);
  const [y2, m2, d2] = toIso.split('-').map(Number);
  return Math.round((Date.UTC(y2, m2 - 1, d2) - Date.UTC(y1, m1 - 1, d1)) / 86400000);
}

/** The message for one form field from a backend validation error. */
export const fieldError = (error, field) => error?.details?.[field] || '';
