// [FRONTEND ROLE RULES HERE]
// How: Mirrors the backend's role ranking (admin > manager > employee) so the
//      interface only shows buttons and pages a user can actually use.
// Why: Showing an "Archive" button that always fails would be confusing. The
//      backend remains the real gatekeeper; this just keeps the UI honest.
const RANK = { employee: 1, manager: 2, admin: 3 };

export const hasRole = (user, role) => (RANK[user?.role] || 0) >= RANK[role];
export const isAdmin = (user) => user?.role === 'admin';
export const isManager = (user) => hasRole(user, 'manager');
export const canManageProject = (user, project) =>
  isAdmin(user) || (user?.role === 'manager' && project?.manager_id === user.id);
