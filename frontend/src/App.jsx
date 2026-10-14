import { Route, Routes } from 'react-router-dom';
import RequireAuth from './auth/RequireAuth.jsx';
import Layout from './components/Layout.jsx';
import AuditLogPage from './pages/AuditLogPage.jsx';
import DashboardPage from './pages/DashboardPage.jsx';
import HoursPage from './pages/HoursPage.jsx';
import LoginPage from './pages/LoginPage.jsx';
import NotFoundPage from './pages/NotFoundPage.jsx';
import PeoplePage from './pages/PeoplePage.jsx';
import PersonPage from './pages/PersonPage.jsx';
import ProfilePage from './pages/ProfilePage.jsx';
import ProjectDetailPage from './pages/ProjectDetailPage.jsx';
import ProjectsPage from './pages/ProjectsPage.jsx';

// [ROUTES HERE]
// How: The login page is public; everything else sits behind RequireAuth
//      inside the shared Layout. People needs manager or above, and the
//      audit log needs admin.
// Why: One table of every page and who can open it, so access rules are
//      easy to read and change in one place.
/** All pages and who can open them. */
export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<Layout />}>
          <Route index element={<DashboardPage />} />
          <Route path="projects" element={<ProjectsPage />} />
          <Route path="projects/:id" element={<ProjectDetailPage />} />
          <Route path="hours" element={<HoursPage />} />
          <Route path="profile" element={<ProfilePage />} />
          <Route path="people/:id" element={<PersonPage />} />
          <Route element={<RequireAuth role="manager" />}>
            <Route path="people" element={<PeoplePage />} />
          </Route>
          <Route element={<RequireAuth role="admin" />}>
            <Route path="audit" element={<AuditLogPage />} />
          </Route>
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
