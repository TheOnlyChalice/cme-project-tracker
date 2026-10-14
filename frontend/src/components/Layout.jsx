import AccountCircleIcon from '@mui/icons-material/AccountCircle';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
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
import { useT } from '../i18n/LanguageContext.js';
import { hasRole } from '../utils/roles.js';
import AppearanceControls from './AppearanceControls.jsx';
import StatusChip from './StatusChip.jsx';

const DRAWER_WIDTH = 240;
const RAIL_WIDTH = 72;
const COLLAPSE_KEY = 'acme.sidebarCollapsed';

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
  const t = useT();
  const navigate = useNavigate();
  const isMobile = useIsMobile();
  const [open, setOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);

  // [COLLAPSIBLE SIDEBAR HERE]
  // How: On desktop, the arrow at the bottom of the sidebar slides it between
  //      full width (icons and labels) and a slim icon-only rail. The width
  //      animates, labels fade, each icon shows its label as a tooltip while
  //      collapsed, and the choice is remembered in the browser.
  // Why: Gives pages more room when wanted while keeping one-click access to
  //      every section. Phones keep the slide-out menu, which already hides
  //      itself.
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(COLLAPSE_KEY) === 'true');
  const toggleCollapsed = () => {
    localStorage.setItem(COLLAPSE_KEY, String(!collapsed));
    setCollapsed(!collapsed);
  };
  const mini = collapsed && !isMobile;
  const width = mini ? RAIL_WIDTH : DRAWER_WIDTH;
  const slide = (theme) => theme.transitions.create(['width', 'opacity'], {
    duration: theme.transitions.duration.standard,
    easing: theme.transitions.easing.easeInOut,
  });
  const labelSx = { opacity: mini ? 0 : 1, transition: slide, whiteSpace: 'nowrap' };
  const navItem = (key, to, icon, label, extra = {}) => {
    const button = (
      <ListItemButton
        key={key}
        component={to ? NavLink : 'div'}
        to={to}
        onClick={() => setOpen(false)}
        sx={{ mx: 1, borderRadius: 2, minHeight: 44, '&.active': { bgcolor: 'action.selected' } }}
        {...extra}
      >
        <ListItemIcon sx={{ minWidth: mini ? 0 : 40, transition: slide }}>{icon}</ListItemIcon>
        <ListItemText primary={label} sx={labelSx} />
      </ListItemButton>
    );
    return mini ? <Tooltip key={key} title={label} placement="right">{button}</Tooltip> : button;
  };

  const items = NAV_ITEMS.filter((item) => hasRole(user, item.role));
  const initials = `${user.first_name?.[0] || ''}${user.last_name?.[0] || ''}`;

  const signOut = async () => {
    setSigningOut(true);
    await logout();
    navigate('/login');
  };

  const menu = (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', overflowX: 'hidden' }}>
      <Toolbar>{isMobile && <Typography variant="h6" noWrap>ACME Tracker</Typography>}</Toolbar>
      <List component="nav" aria-label={t('Main navigation')} sx={{ flexGrow: 1, pt: 1 }}>
        {items.map((item) => navItem(item.to, item.to, item.icon, t(item.label), { end: item.end }))}
      </List>
      <Divider />
      <List>
        {navItem('profile', '/profile', <AccountCircleIcon />, t('My profile'))}
        {navItem('signout', null, <LogoutIcon />, signingOut ? t('Signing out…') : t('Sign out'),
          { onClick: signOut, disabled: signingOut, role: 'button' })}
      </List>
      {!isMobile && (
        <>
          <Divider />
          <Box sx={{ display: 'flex', justifyContent: mini ? 'center' : 'flex-end', p: 1 }}>
            <Tooltip title={mini ? t('Expand menu') : t('Collapse menu')} placement="right">
              <IconButton onClick={toggleCollapsed} aria-label={mini ? t('Expand menu') : t('Collapse menu')}
                aria-expanded={!mini}>
                {mini ? <ChevronRightIcon /> : <ChevronLeftIcon />}
              </IconButton>
            </Tooltip>
          </Box>
        </>
      )}
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100%' }}>
      {/* [BRAND TOP BAR HERE]
          How: The top bar is ACME dark blue with white text in both modes, and
               its controls switch to white so they stay readable on it.
          Why: A solid brand-colored header ties the app to ACME's dark blue
               and white identity whichever mode is chosen. */}
      <AppBar position="fixed" elevation={0}
        sx={{ bgcolor: 'brand.bar', color: '#ffffff', zIndex: (theme) => theme.zIndex.drawer + 1 }}>
        <Toolbar sx={{ gap: 1 }}>
          {isMobile && (
            <IconButton edge="start" color="inherit" aria-label={t('Open menu')} onClick={() => setOpen(true)}>
              <MenuIcon />
            </IconButton>
          )}
          <Typography variant="h6" sx={{ flexGrow: 1 }} noWrap>
            {isMobile ? 'ACME' : 'ACME Project Tracker'}
          </Typography>
          <AppearanceControls inverse />
          {!isMobile && <StatusChip value={user.role} inverse />}
          <Tooltip title={`${user.first_name} ${user.last_name} (${user.username})`}>
            <Avatar
              src={user.profile_picture_url || undefined}
              sx={{ ml: 1, width: 34, height: 34, bgcolor: 'secondary.main', color: 'secondary.contrastText', cursor: 'pointer' }}
              onClick={() => navigate('/profile')}
            >
              {initials}
            </Avatar>
          </Tooltip>
        </Toolbar>
      </AppBar>

      <Box component="nav" sx={{ width: { md: width }, flexShrink: { md: 0 }, transition: slide }}>
        <Drawer
          variant={isMobile ? 'temporary' : 'permanent'}
          open={isMobile ? open : true}
          onClose={() => setOpen(false)}
          ModalProps={{ keepMounted: true }}
          sx={{ '& .MuiDrawer-paper': { width: isMobile ? DRAWER_WIDTH : width, boxSizing: 'border-box', transition: slide, overflowX: 'hidden' } }}
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
