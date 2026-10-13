// Shared display helpers so dates, money, and hours look the same everywhere.

export function formatDate(value) {
  if (!value) return '—';
  const [year, month, day] = String(value).slice(0, 10).split('-').map(Number);
  return new Date(year, month - 1, day).toLocaleDateString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric',
  });
}

export function formatDateTime(value) {
  if (!value) return '—';
  return new Date(value).toLocaleString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit',
  });
}

export function formatMoney(value) {
  if (value === null || value === undefined) return '—';
  return Number(value).toLocaleString(undefined, { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });
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

/** The message for one form field from a backend validation error. */
export const fieldError = (error, field) => error?.details?.[field] || '';
