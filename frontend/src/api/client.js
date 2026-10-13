import { clearSession, loadSession, saveSession } from './session.js';

// [API BASE URL HERE]
// How: VITE_API_URL comes from frontend/.env.local locally, and from
//      ./bin/deploy-frontend.sh (your CloudFront address) when deployed.
// Why: The same code talks to the local Python dev server or to Lambda
//      without any changes; only the build setting differs.
const API_BASE = `${(import.meta.env.VITE_API_URL || '').replace(/\/$/, '')}/api/v1`;

export class ApiError extends Error {
  constructor(status, code, message, details) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details || {};
  }
}

let onSessionEnded = () => {};

// [REQUEST ACTIVITY TRACKER HERE]
// How: Counts requests that are still waiting for an answer and tells any
//      listener when the count changes.
// Why: Powers the progress bar at the top of the screen, so there is always
//      a visible sign that something is processing, on every page and for
//      every action, without each page having to remember to show one.
let pending = 0;
const listeners = new Set();

function setPending(change) {
  pending += change;
  listeners.forEach((listener) => listener());
}

/** Subscribe to changes in the number of in-flight requests. */
export function subscribeToActivity(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** How many requests are currently in flight. */
export const pendingRequests = () => pending;

/** Lets the auth provider know when the session can no longer be renewed. */
export function setSessionEndedHandler(handler) {
  onSessionEnded = handler;
}

async function parse(response) {
  const type = response.headers.get('content-type') || '';
  // [CLOUDFRONT 404 GUARD HERE]
  // How: Anything that isn't JSON is treated as "not found".
  // Why: CloudFront is set up to answer every 404 with the website's
  //      index.html (so page links work), and that includes 404s from the API.
  //      Without this check, a missing project would look like a successful
  //      response containing a web page.
  if (!type.includes('application/json')) {
    if (response.ok && response.status !== 204) {
      throw new ApiError(404, 'not_found', 'Not found.');
    }
    if (!response.ok) {
      throw new ApiError(response.status, 'http_error', `Request failed (${response.status}).`);
    }
    return null;
  }
  const body = await response.json();
  if (!response.ok) {
    const error = body?.error || {};
    throw new ApiError(response.status, error.code || 'http_error',
      error.message || `Request failed (${response.status}).`, error.details);
  }
  return body;
}

let refreshing = null;

// [TOKEN REFRESH FLOW HERE]
// How: When a request fails with "token_expired", the refresh token is traded
//      for a new pair, saved, and the original request is retried once. If
//      several requests expire at the same moment, they share one refresh.
// Why: Access tokens last an hour. This keeps people working without being
//      kicked out mid-task, and sharing one refresh avoids racing requests
//      that would each try to refresh separately.
async function refreshTokens() {
  if (!refreshing) {
    refreshing = (async () => {
      const session = loadSession();
      if (!session?.refresh_token) throw new ApiError(401, 'no_session', 'Please sign in.');
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: session.refresh_token }),
      });
      const body = await parse(response);
      saveSession(body);
      return body;
    })().finally(() => {
      refreshing = null;
    });
  }
  return refreshing;
}

/**
 * Call the backend API.
 * @param {string} path e.g. "/projects"
 * @param {{method?: string, body?: any, query?: object, auth?: boolean}} options
 */
export async function api(path, { method = 'GET', body, query, auth = true } = {}, retried = false) {
  const url = new URL(`${API_BASE}${path}`, window.location.origin);
  Object.entries(query || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, value);
  });

  // [AUTH HEADER HERE]
  // How: Every request automatically carries "Authorization: Bearer <token>".
  // Why: Pages never handle tokens themselves, so no page can forget to sign
  //      its requests.
  const headers = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const session = loadSession();
  if (auth && session?.access_token) headers.Authorization = `Bearer ${session.access_token}`;

  let response;
  setPending(1);
  try {
    response = await fetch(url, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, 'network_error', 'Could not reach the server. Check your connection.');
  } finally {
    setPending(-1);
  }

  try {
    return await parse(response);
  } catch (error) {
    if (auth && !retried && error.code === 'token_expired') {
      try {
        await refreshTokens();
      } catch {
        clearSession();
        onSessionEnded(error);
        throw error;
      }
      return api(path, { method, body, query, auth }, true);
    }
    if (auth && error.status === 401 && ['token_revoked', 'invalid_user', 'invalid_token'].includes(error.code)) {
      clearSession();
      onSessionEnded(error);
    }
    // [COLD START RETRY HERE]
    // How: A 503 "storage_unavailable" is retried once after a short pause.
    // Why: The first request after Aurora has been idle can time out while
    //      the database wakes up; one quiet retry hides that from the user.
    if (!retried && error.code === 'storage_unavailable') {
      await new Promise((resolve) => setTimeout(resolve, 1500));
      return api(path, { method, body, query, auth }, true);
    }
    throw error;
  }
}
