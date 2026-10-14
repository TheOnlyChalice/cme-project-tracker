// [ACME: SESSION STORAGE HERE]
// How: The access token, refresh token, and signed-in user are saved together
//      in the browser's localStorage under one key.
// Why: Keeps people signed in when they refresh the page or come back later
//      (until the 7-day refresh token runs out). The access token itself only
//      lasts an hour, and logging out cancels both tokens on the server, which
//      limits the damage if one were ever copied.
const KEY = 'cme.session';

export function loadSession() {
  try {
    return JSON.parse(localStorage.getItem(KEY)) || null;
  } catch {
    return null;
  }
}

export function saveSession(session) {
  localStorage.setItem(KEY, JSON.stringify(session));
}

export function clearSession() {
  localStorage.removeItem(KEY);
}
