import { createContext, useContext } from 'react';

export const AuthContext = createContext(null);

/** Access the signed-in user and the login/logout functions. */
export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside <AuthProvider>');
  return value;
}
