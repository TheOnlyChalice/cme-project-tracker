import { Navigate, Outlet, useLocation } from 'react-router-dom';
import PropTypes from 'prop-types';
import Loading from '../components/Loading.jsx';
import { hasRole } from '../utils/roles.js';
import { useAuth } from './AuthContext.js';

// [ROUTE GUARD HERE]
// How: Wraps protected pages. Signed-out visitors are sent to the login page
//      (and returned afterwards); signed-in users without the needed role are
//      sent to the dashboard.
// Why: Hiding pages is only for a clean experience. The backend still checks
//      every request, so nothing is protected by the frontend alone.
/** Only renders child pages for signed-in users with the needed role. */
export default function RequireAuth({ role }) {
  const { user, checking } = useAuth();
  const location = useLocation();
  if (checking) return <Loading label="Checking your session" />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (role && !hasRole(user, role)) return <Navigate to="/" replace />;
  return <Outlet />;
}

RequireAuth.propTypes = {
  role: PropTypes.oneOf(['employee', 'manager', 'admin']),
};
