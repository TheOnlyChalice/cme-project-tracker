import { useCallback, useEffect, useMemo, useState } from 'react';
import PropTypes from 'prop-types';
import { api, setSessionEndedHandler } from '../api/client.js';
import { clearSession, loadSession, saveSession } from '../api/session.js';
import { AuthContext } from './AuthContext.js';

// [AUTH PROVIDER HERE]
// How: Holds the signed-in user for the whole app. On start-up it restores a
//      saved session and confirms it with GET /me; login saves the tokens;
//      logout tells the server to cancel the tokens, then clears them locally.
// Why: Every page needs to know who's signed in and their role. Confirming
//      with /me on start-up catches sessions that were revoked elsewhere
//      (for example, after a password change on another device).
/** Provides the signed-in user and sign-in actions to the app. */
export default function AuthProvider({ children }) {
  const [user, setUser] = useState(() => loadSession()?.user || null);
  const [checking, setChecking] = useState(() => Boolean(loadSession()));
  const [notice, setNotice] = useState('');

  useEffect(() => {
    setSessionEndedHandler((message) => {
      setUser(null);
      setNotice(message);
    });
    if (!loadSession()) return;
    api('/me')
      .then((me) => {
        const session = loadSession();
        if (session) saveSession({ ...session, user: me });
        setUser(me);
      })
      .catch(() => {
        clearSession();
        setUser(null);
      })
      .finally(() => setChecking(false));
  }, []);

  const login = useCallback(async (username, password) => {
    const session = await api('/auth/login', { method: 'POST', body: { username, password }, auth: false });
    saveSession(session);
    setNotice('');
    setUser(session.user);
    return session.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api('/auth/logout', { method: 'POST' });
    } catch {
      // Already signed out on the server; clearing locally is enough.
    }
    clearSession();
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    const me = await api('/me');
    const session = loadSession();
    if (session) saveSession({ ...session, user: me });
    setUser(me);
    return me;
  }, []);

  const value = useMemo(
    () => ({ user, checking, notice, login, logout, refreshUser }),
    [user, checking, notice, login, logout, refreshUser],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

AuthProvider.propTypes = {
  children: PropTypes.node,
};
