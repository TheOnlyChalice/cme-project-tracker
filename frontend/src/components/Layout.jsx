import AccountCircleIcon from '@mui/icons-material/AccountCircle';
import DashboardIcon from '@mui/icons-material/Dashboard';
import FolderIcon from '@mui/icons-material/Folder';
import HistoryIcon from '@mui/icons-material/History';
import LogoutIcon from '@mui/icons-material/Logout';
import MenuIcon from '@mui/icons-material/Menu';
import PeopleIcon from '@mui/icons-material/People';
import ScheduleIcon from '@mui/icons-material/Schedule';
import {
  AppBar, Avatar, Box, Divider, Drawer, IconButton, List, ListItemButton, ListItemIcon,
  ListItemText, Toolbar, Tooltip, Typography,
} from '@mui/material';
import { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext.js';
import useIsMobile from '../hooks/useIsMobile.js';
import { hasRole } from '../utils/roles.js';
import StatusChip from './StatusChip.jsx';

const DRAWER_WIDTH = 240;

// [ROLE-BASED NAVIGATION HERE]
// How: Each menu item lists the lowest role that can use it, and the menu
//      only shows items the signed-in user's role allows.
// Why: Employees never see admin-only pages like the audit log, which keeps
//      the menu simple and matches what the backend will actually allow.
const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: <DashboardIcon />, role: 'employee', end: true },
  { to: '/projects', label: 'Projects', icon: <FolderIcon />, role: 'employee' },
  { to: '/hours', label: 'Hours', icon: <ScheduleIcon />, role: 'employee' },
  { to: '/people', label: 'People', icon: <PeopleIcon />, role: 'manager' },
  { to: '/audit', label: 'Audit log', icon: <HistoryIcon />, role: 'admin' },
];

// [RESPONSIVE LAYOUT HERE]
// How: On desktops the menu is a permanent sidebar; on phones and small
//      tablets (under 900px, via React Responsive) it becomes a slide-out
//      drawer opened from the menu button in the top bar.
// Why: A fixed sidebar would take up most of a phone screen. The same menu
//      component serves both, so the two versions can never get out of sync.
/** The signed-in app frame: top bar, navigation menu, and page area. */
export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const isMobile = useIsMobile();
  const [open, setOpen] = useState(false);

  const items = NAV_ITEMS.filter((item) => hasRole(user, item.role));
  const initials = `${user.first_name?.[0] || ''}${user.last_name?.[0] || ''}`;

  const signOut = async () => {
    await logout();
    navigate('/login');
  };

  const menu = (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Toolbar>
        <Typography variant="h6" noWrap>ACME Tracker</Typography>
      </Toolbar>
      <Divider />
      <List component="nav" aria-label="Main navigation" sx={{ flexGrow: 1 }}>
        {items.map((item) => (
          <ListItemButton
            key={item.to}
            component={NavLink}
            to={item.to}
            end={item.end}
            onClick={() => setOpen(false)}
            sx={{ mx: 1, borderRadius: 2, '&.active': { bgcolor: 'action.selected' } }}
          >
            <ListItemIcon>{item.icon}</ListItemIcon>
            <ListItemText primary={item.label} />
          </ListItemButton>
        ))}
      </List>
      <Divider />
      <List>
        <ListItemButton component={NavLink} to="/profile" onClick={() => setOpen(false)} sx={{ mx: 1, borderRadius: 2 }}>
          <ListItemIcon><AccountCircleIcon /></ListItemIcon>
          <ListItemText primary="My profile" />
        </ListItemButton>
        <ListItemButton onClick={signOut} sx={{ mx: 1, borderRadius: 2 }}>
          <ListItemIcon><LogoutIcon /></ListItemIcon>
          <ListItemText primary="Sign out" />
        </ListItemButton>
      </List>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100%' }}>
      <AppBar position="fixed" color="inherit" sx={{ borderBottom: 1, borderColor: 'divider', zIndex: (t) => t.zIndex.drawer + 1 }}>
        <Toolbar>
          {isMobile && (
            <IconButton edge="start" aria-label="Open menu" onClick={() => setOpen(true)} sx={{ mr: 1 }}>
              <MenuIcon />
            </IconButton>
          )}
          <Typography variant="h6" sx={{ flexGrow: 1 }} noWrap>
            {isMobile ? 'ACME Tracker' : 'ACME Project Tracker'}
          </Typography>
          {!isMobile && <StatusChip value={user.role} />}
          <Tooltip title={`${user.first_name} ${user.last_name} (${user.username})`}>
            <Avatar
              src={user.profile_picture_url || undefined}
              sx={{ ml: 2, width: 34, height: 34, bgcolor: 'primary.main', cursor: 'pointer' }}
              onClick={() => navigate('/profile')}
            >
              {initials}
            </Avatar>
          </Tooltip>
        </Toolbar>
      </AppBar>

      <Box component="nav" sx={{ width: { md: DRAWER_WIDTH }, flexShrink: { md: 0 } }}>
        <Drawer
          variant={isMobile ? 'temporary' : 'permanent'}
          open={isMobile ? open : true}
          onClose={() => setOpen(false)}
          ModalProps={{ keepMounted: true }}
          sx={{ '& .MuiDrawer-paper': { width: DRAWER_WIDTH, boxSizing: 'border-box' } }}
        >
          {menu}
        </Drawer>
      </Box>

      <Box component="main" sx={{ flexGrow: 1, minWidth: 0, p: { xs: 2, md: 3 } }}>
        <Toolbar />
        <Outlet />
      </Box>
    </Box>
  );
}
