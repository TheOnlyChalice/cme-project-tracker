import FlagIcon from '@mui/icons-material/FlagOutlined';
import FolderIcon from '@mui/icons-material/FolderOutlined';
import PersonIcon from '@mui/icons-material/PersonOutline';
import SearchIcon from '@mui/icons-material/Search';
import {
  Box, CircularProgress, ClickAwayListener, InputBase, List, ListItemButton, ListItemIcon, ListItemText,
  ListSubheader, Paper, Popper, Typography,
} from '@mui/material';
import PropTypes from 'prop-types';
import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client.js';
import useDebouncedValue from '../hooks/useDebouncedValue.js';
import { useT } from '../i18n/LanguageContext.js';
import { formatDate } from '../utils/format.js';

const LIST_ID = 'quick-search-results';
const ROLE_LABELS = { admin: 'Admin', manager: 'Manager', employee: 'Employee' };

/** Bold the part of a name that matches what was typed. */
function Highlight({ text, query }) {
  const at = text.toLowerCase().indexOf(query.toLowerCase());
  if (!query || at < 0) return text;
  return (
    <>
      {text.slice(0, at)}
      <Box component="mark" sx={{ bgcolor: 'transparent', color: 'inherit', fontWeight: 700 }}>{text.slice(at, at + query.length)}</Box>
      {text.slice(at + query.length)}
    </>
  );
}

Highlight.propTypes = {
  text: PropTypes.string.isRequired,
  query: PropTypes.string.isRequired,
};

// [ACME: QUICK SEARCH BOX HERE]
// How: As you type (after 2 letters, with a short pause), the box asks the
//      backend's /search and shows a dropdown grouped into Projects,
//      Milestones, and People, with the matching letters in bold. Arrow keys
//      move through results, Enter opens one (projects open their page,
//      milestones open their project scrolled to the milestone, people open
//      their person page), Escape closes, and Ctrl+K jumps here from
//      anywhere. The last row searches the full project list instead.
// Why: People remember things by different handles: a person, a milestone,
//      a project. One box that finds any of them, and works without a mouse,
//      is the quickest way around the app. It's built as an accessible
//      combobox, so screen readers announce the results and the highlighted one.
/** Live search across projects, milestones, and people. */
export default function QuickSearch({ autoFocus = false, onDone }) {
  const t = useT();
  const navigate = useNavigate();
  const anchor = useRef(null);
  const input = useRef(null);
  const [value, setValue] = useState('');
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const [state, setState] = useState({ query: '', results: null, loading: false });
  const query = useDebouncedValue(value.trim(), 200);

  useEffect(() => {
    const onKey = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        input.current?.focus();
        setOpen(true);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  useEffect(() => {
    if (query.length < 2) return undefined;
    let current = true;
    api('/search', { query: { q: query } })
      .then((results) => current && setState({ query, results, loading: false }))
      .catch(() => current && setState({ query, results: null, loading: false }));
    return () => {
      current = false;
    };
  }, [query]);

  const ready = query.length >= 2 && state.query === query && state.results;
  const loading = query.length >= 2 && state.query !== query;
  const results = ready ? state.results : { projects: [], milestones: [], people: [] };
  const items = [
    ...results.projects.map((r) => ({ kind: 'project', key: `p-${r.id}`, ...r })),
    ...results.milestones.map((r) => ({ kind: 'milestone', key: `m-${r.id}`, ...r })),
    ...results.people.map((r) => ({ kind: 'person', key: `u-${r.id}`, ...r })),
  ];
  if (query.length >= 2) items.push({ kind: 'all', key: 'all' });
  const activeItem = items[active];

  const finish = () => {
    setOpen(false);
    setValue('');
    setActive(-1);
    onDone?.();
  };

  const go = (item) => {
    if (!item) return;
    if (item.kind === 'project') navigate(`/projects/${item.id}`);
    if (item.kind === 'milestone') navigate(`/projects/${item.project_id}?milestone=${item.id}`);
    if (item.kind === 'person') navigate(`/people/${item.id}`);
    if (item.kind === 'all') navigate(`/projects?search=${encodeURIComponent(query)}`);
    finish();
  };

  const onKeyDown = (event) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setOpen(true);
      setActive((i) => (items.length ? (i + 1) % items.length : -1));
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActive((i) => (items.length ? (i - 1 + items.length) % items.length : -1));
    } else if (event.key === 'Enter') {
      event.preventDefault();
      go(activeItem || items[items.length - 1]);
    } else if (event.key === 'Escape') {
      setOpen(false);
      setActive(-1);
    }
  };

  const optionProps = (item) => {
    const index = items.indexOf(item);
    return {
      id: `${LIST_ID}-${item.key}`,
      role: 'option',
      'aria-selected': index === active,
      selected: index === active,
      onMouseEnter: () => setActive(index),
      onClick: () => go(item),
      sx: { borderRadius: 2, mx: 0.75 },
    };
  };

  const group = (title, kind, total, icon, describe) => {
    const groupItems = items.filter((item) => item.kind === kind);
    if (!groupItems.length) return null;
    return (
      <li key={kind}>
        <List disablePadding role="group" aria-label={t(title)}>
          <ListSubheader sx={{ lineHeight: '32px', bgcolor: 'background.paper', fontWeight: 700 }}>
            {t(title)}{total > groupItems.length ? ` · ${t('top {shown} of {total}', { shown: groupItems.length, total })}` : ''}
          </ListSubheader>
          {groupItems.map((item) => (
            <ListItemButton key={item.key} {...optionProps(item)}>
              <ListItemIcon sx={{ minWidth: 36, color: 'text.secondary' }}>{icon}</ListItemIcon>
              <ListItemText
                primary={<Highlight text={item.name} query={query} />}
                secondary={describe(item)}
                primaryTypographyProps={{ noWrap: true, fontWeight: 500 }}
                secondaryTypographyProps={{ noWrap: true }}
              />
            </ListItemButton>
          ))}
        </List>
      </li>
    );
  };

  const showPanel = open && query.length >= 2;

  return (
    <ClickAwayListener onClickAway={() => setOpen(false)}>
      <Box ref={anchor} sx={{ flex: '1 1 260px', maxWidth: 480, position: 'relative' }}>
        <Box sx={{
          display: 'flex', alignItems: 'center', gap: 1, px: 1.5, height: 44, borderRadius: 2.5,
          bgcolor: 'background.default', border: 1, borderColor: showPanel ? 'primary.main' : 'divider',
        }}>
          <SearchIcon fontSize="small" sx={{ color: 'text.secondary' }} />
          <InputBase
            inputRef={input}
            autoFocus={autoFocus}
            value={value}
            onChange={(event) => { setValue(event.target.value); setOpen(true); setActive(-1); }}
            onFocus={() => setOpen(true)}
            onKeyDown={onKeyDown}
            placeholder={t('Search projects, milestones, people')}
            sx={{ flexGrow: 1, fontSize: 14 }}
            inputProps={{
              role: 'combobox',
              'aria-label': t('Quick search'),
              'aria-expanded': showPanel,
              'aria-controls': LIST_ID,
              'aria-autocomplete': 'list',
              'aria-activedescendant': activeItem ? `${LIST_ID}-${activeItem.key}` : undefined,
            }}
          />
          {loading
            ? <CircularProgress size={16} aria-label={t('Loading')} />
            : (
              <Box component="kbd" sx={{ fontFamily: 'inherit', fontSize: 12, color: 'text.secondary', border: 1, borderColor: 'divider', borderRadius: 1.5, px: 0.75 }}>
                Ctrl K
              </Box>
            )}
        </Box>
        <Popper open={showPanel} anchorEl={anchor.current} placement="bottom-start" disablePortal
          sx={{ zIndex: (theme) => theme.zIndex.modal, width: anchor.current?.offsetWidth || 360 }}>
          <Paper variant="outlined" sx={{ mt: 0.75, maxHeight: '70vh', overflowY: 'auto', borderRadius: 3, boxShadow: '0 12px 32px rgba(8,26,56,0.18)' }}>
            <List id={LIST_ID} role="listbox" aria-label={t('Search results')} sx={{ py: 0.75 }}>
              {group('Projects', 'project', results.totals?.projects || 0, <FolderIcon />, (r) => (
                `${r.is_archived ? `${t('Archived')} · ` : ''}${t('Ends {date}', { date: formatDate(r.end_date) })}`
              ))}
              {group('Milestones', 'milestone', results.totals?.milestones || 0, <FlagIcon />, (r) => (
                `${r.project_name} · ${t('Due {date}', { date: formatDate(r.end_date) })}`
              ))}
              {group('People', 'person', results.totals?.people || 0, <PersonIcon />, (r) => (
                `${r.job_title || t(ROLE_LABELS[r.role])} · ${r.username}`
              ))}
              {ready && items.length === 1 && (
                <Typography sx={{ px: 2, py: 1.5 }} color="text.secondary">{t('No matches for "{query}".', { query })}</Typography>
              )}
              {query.length >= 2 && (
                <ListItemButton {...optionProps(items[items.length - 1])}>
                  <ListItemIcon sx={{ minWidth: 36, color: 'text.secondary' }}><SearchIcon /></ListItemIcon>
                  <ListItemText primary={t('Search all projects for "{query}"', { query })} />
                </ListItemButton>
              )}
            </List>
          </Paper>
        </Popper>
      </Box>
    </ClickAwayListener>
  );
}

QuickSearch.propTypes = {
  autoFocus: PropTypes.bool,
  onDone: PropTypes.func,
};
