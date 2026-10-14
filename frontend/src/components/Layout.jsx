import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import CloseIcon from '@mui/icons-material/Close';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import DashboardIcon from '@mui/icons-material/SpaceDashboardOutlined';
import FolderIcon from '@mui/icons-material/FolderOutlined';
import HistoryIcon from '@mui/icons-material/HistoryOutlined';
import LogoutIcon from '@mui/icons-material/LogoutOutlined';
import MenuIcon from '@mui/icons-material/Menu';
import SearchIcon from '@mui/icons-material/Search';
import PeopleIcon from '@mui/icons-material/PeopleOutline';
import PersonIcon from '@mui/icons-material/PersonOutline';
import ScheduleIcon from '@mui/icons-material/ScheduleOutlined';
import {
  AppBar, Avatar, Box, Dialog, DialogContent, Drawer, IconButton, List, ListItemButton, ListItemIcon, ListItemText,
  Toolbar, Tooltip, Typography,
} from '@mui/material';
import { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext.js';
import useIsMobile from '../hooks/useIsMobile.js';
import { useT } from '../i18n/LanguageContext.js';
import { hasRole } from '../utils/roles.js';
import AppearanceControls from './AppearanceControls.jsx';
import BrandMark from './BrandMark.jsx';
import QuickSearch from './QuickSearch.jsx';

const DRAWER_WIDTH = 248;
const RAIL_WIDTH = 76;
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

const ROLE_LABELS = { admin: 'Admin', manager: 'Manager', employee: 'Employee' };

// [NAVY SIDEBAR HERE]
// How: The sidebar is ACME navy in both light and dark mode, with the logo
//      at the top, white menu items (the active one highlighted, its icon in
//      amber), and a card at the bottom with the signed-in person, their
//      role, sign-out, and the collapse arrow.
// Why: A dark brand-colored frame around a light work area is the core of
//      the "command center" look, and keeping identity and sign-out in one
//      place frees the top bar for search and settings.

// [COLLAPSIBLE SIDEBAR HERE]
// How: On desktop the arrow slides the sidebar between full width and an
//      icon-only rail; the width animates, labels fade, icons show their
//      label as a tooltip, and the choice is remembered in the browser.
//      Phones get a slide-out menu from the top bar's menu button instead.
// Why: More room for the timeline and tables when wanted, with every section
//      still one click away.
/** The signed-in app frame: navy sidebar, top bar, and page area. */
export default function Layout() {
  const { user, logout } = useAuth();
  const t = useT();
  const navigate = useNavigate();
  const isMobile = useIsMobile();
  const [open, setOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(COLLAPSE_KEY) === 'true');
  const [searching, setSearching] = useState(false);

  const mini = collapsed && !isMobile;
  const width = mini ? RAIL_WIDTH : DRAWER_WIDTH;
  const slide = (theme) => theme.transitions.create(['width', 'opacity', 'margin'], {
    duration: theme.transitions.duration.standard,
    easing: theme.transitions.easing.easeInOut,
  });
  const fade = { opacity: mini ? 0 : 1, transition: slide, whiteSpace: 'nowrap' };
  const initials = `${user.first_name?.[0] || ''}${user.last_name?.[0] || ''}`;
  const items = NAV_ITEMS.filter((item) => hasRole(user, item.role));

  const toggleCollapsed = () => {
    localStorage.setItem(COLLAPSE_KEY, String(!collapsed));
    setCollapsed(!collapsed);
  };

  const signOut = async () => {
    setSigningOut(true);
    await logout();
    navigate('/login');
  };

  const navButton = (key, props, icon, label) => {
    const button = (
      <ListItemButton
        key={key}
        onClick={() => setOpen(false)}
        {...props}
        sx={{
          mx: 1.25, mb: 0.5, borderRadius: 2.5, minHeight: 46, color: 'brand.sidebarMuted',
          justifyContent: mini ? 'center' : 'flex-start',
          '&:hover': { bgcolor: 'rgba(255,255,255,0.06)', color: 'brand.sidebarText' },
          '&.active': { bgcolor: 'brand.sidebarActive', color: 'brand.sidebarText', fontWeight: 600 },
          '&.active .MuiListItemIcon-root': { color: 'brand.accent' },
        }}
      >
        <ListItemIcon sx={{ minWidth: mini ? 0 : 38, color: 'inherit', transition: slide }}>{icon}</ListItemIcon>
        <ListItemText primary={label} sx={{ ...fade, display: mini ? 'none' : 'block' }}
          primaryTypographyProps={{ fontWeight: 'inherit' }} />
      </ListItemButton>
    );
    return mini ? <Tooltip key={key} title={label} placement="right">{button}</Tooltip> : button;
  };

  const menu = (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', overflowX: 'hidden', py: 2.5 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, px: mini ? 0 : 2.5, pb: 3, justifyContent: mini ? 'center' : 'flex-start' }}>
        <BrandMark size={38} />
        <Box sx={{ ...fade, display: mini ? 'none' : 'flex', flexDirection: 'column' }}>
          <Typography sx={{ fontFamily: (theme) => theme.typography.h6.fontFamily, fontWeight: 700, fontSize: 19, lineHeight: 1.1, color: 'brand.sidebarText' }}>ACME</Typography>
          <Typography sx={{ fontSize: 12, color: 'brand.sidebarMuted' }}>{t('Project Tracker')}</Typography>
        </Box>
      </Box>

      <List component="nav" aria-label={t('Main navigation')} sx={{ flexGrow: 1, py: 0 }}>
        {items.map((item) => navButton(item.to, { component: NavLink, to: item.to, end: item.end }, item.icon, t(item.label)))}
      </List>

      <List sx={{ py: 0 }}>
        {navButton('profile', { component: NavLink, to: '/profile' }, <PersonIcon />, t('My profile'))}
        {navButton('signout', { onClick: signOut, disabled: signingOut }, <LogoutIcon />, signingOut ? t('Signing out…') : t('Sign out'))}
      </List>

      <Box sx={{
        mx: 1.25, mt: 1.5, p: mini ? 1 : 1.5, borderRadius: 3, bgcolor: 'rgba(255,255,255,0.06)',
        display: 'flex', alignItems: 'center', gap: 1.25, flexDirection: mini ? 'column' : 'row',
      }}>
        <Avatar src={user.profile_picture_url || undefined}
          sx={{ width: 36, height: 36, fontSize: 14, fontWeight: 600, bgcolor: '#7cb8ff', color: '#081a38' }}>
          {initials}
        </Avatar>
        <Box sx={{ ...fade, display: mini ? 'none' : 'flex', flexDirection: 'column', minWidth: 0, flexGrow: 1 }}>
          <Typography noWrap sx={{ fontWeight: 600, fontSize: 14, color: 'brand.sidebarText' }}>
            {user.first_name} {user.last_name}
          </Typography>
          <Typography noWrap sx={{ fontSize: 12, color: 'brand.sidebarMuted' }}>{t(ROLE_LABELS[user.role])}</Typography>
        </Box>
        {!isMobile && (
          <Tooltip title={mini ? t('Expand menu') : t('Collapse menu')} placement="right">
            <IconButton onClick={toggleCollapsed} aria-label={mini ? t('Expand menu') : t('Collapse menu')} aria-expanded={!mini}
              sx={{ color: 'brand.sidebarText', border: 1, borderColor: 'rgba(255,255,255,0.18)', borderRadius: 2.5, width: 40, height: 40 }}>
              {mini ? <ChevronRightIcon /> : <ChevronLeftIcon />}
            </IconButton>
          </Tooltip>
        )}
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100%' }}>
      <Box component="nav" sx={{ width: { md: width }, flexShrink: { md: 0 }, transition: slide }}>
        <Drawer
          variant={isMobile ? 'temporary' : 'permanent'}
          open={isMobile ? open : true}
          onClose={() => setOpen(false)}
          ModalProps={{ keepMounted: true }}
          sx={{
            '& .MuiDrawer-paper': {
              width: isMobile ? DRAWER_WIDTH : width, boxSizing: 'border-box', transition: slide,
              overflowX: 'hidden', bgcolor: 'brand.sidebar', color: 'brand.sidebarText', borderRight: 'none',
            },
          }}
        >
          {menu}
        </Drawer>
      </Box>

      <Box sx={{ flexGrow: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
        <AppBar position="sticky" color="inherit" elevation={0}
          sx={{ bgcolor: 'background.paper', borderBottom: 1, borderColor: 'divider' }}>
          <Toolbar sx={{ gap: 1.5, flexWrap: 'wrap', py: 1, px: { xs: 2, md: 4 } }}>
            {isMobile && (
              <IconButton edge="start" aria-label={t('Open menu')} onClick={() => setOpen(true)}>
                <MenuIcon />
              </IconButton>
            )}
            {isMobile ? (
              <>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexGrow: 1 }}>
                  <BrandMark size={28} />
                  <Typography variant="h6" noWrap>ACME</Typography>
                </Box>
                <IconButton aria-label={t('Quick search')} onClick={() => setSearching(true)}><SearchIcon /></IconButton>
              </>
            ) : (
              <>
                <QuickSearch />
                <Box sx={{ flexGrow: 1 }} />
              </>
            )}
            <AppearanceControls />
          </Toolbar>
        </AppBar>
        {/* On phones, quick search opens full screen from the top bar's search icon. */}
        <Dialog fullScreen open={searching} onClose={() => setSearching(false)} aria-label={t('Quick search')}>
          <DialogContent sx={{ pt: 2 }}>
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-start' }}>
              <QuickSearch autoFocus onDone={() => setSearching(false)} />
              <IconButton aria-label={t('Close')} onClick={() => setSearching(false)}><CloseIcon /></IconButton>
            </Box>
          </DialogContent>
        </Dialog>
        <Box component="main" sx={{ flexGrow: 1, p: { xs: 2, md: 4 }, maxWidth: 1320, width: '100%', boxSizing: 'border-box' }}>
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
}
