import SearchIcon from '@mui/icons-material/Search';
import { Box, InputBase } from '@mui/material';
import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useT } from '../i18n/LanguageContext.js';

// [GLOBAL SEARCH HERE]
// How: A search box in the top bar. Pressing Enter opens the Projects page
//      filtered by what was typed, and Ctrl+K (or Cmd+K) jumps to the box
//      from anywhere.
// Why: The quickest way to get to a project, and a keyboard shortcut that
//      makes the app feel fast to power users. Search still runs on the
//      backend, so it only ever finds projects the user may see.
/** Top-bar project search with a Ctrl+K shortcut. */
export default function GlobalSearch() {
  const t = useT();
  const navigate = useNavigate();
  const input = useRef(null);
  const [value, setValue] = useState('');

  useEffect(() => {
    const onKey = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        input.current?.focus();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const submit = (event) => {
    event.preventDefault();
    navigate(`/projects?search=${encodeURIComponent(value.trim())}`);
  };

  return (
    <Box component="form" role="search" onSubmit={submit}
      sx={{
        flex: '1 1 260px', maxWidth: 440, display: 'flex', alignItems: 'center', gap: 1,
        px: 1.5, height: 44, borderRadius: 2.5, bgcolor: 'background.default',
        border: 1, borderColor: 'divider',
      }}
    >
      <SearchIcon fontSize="small" sx={{ color: 'text.secondary' }} />
      <InputBase
        inputRef={input}
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder={t('Search projects')}
        inputProps={{ 'aria-label': t('Search projects') }}
        sx={{ flexGrow: 1, fontSize: 14 }}
      />
      <Box component="kbd" sx={{ fontFamily: 'inherit', fontSize: 12, color: 'text.secondary', border: 1, borderColor: 'divider', borderRadius: 1.5, px: 0.75 }}>
        Ctrl K
      </Box>
    </Box>
  );
}
