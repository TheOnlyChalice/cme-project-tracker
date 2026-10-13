import { LinearProgress } from '@mui/material';
import { useSyncExternalStore } from 'react';
import { pendingRequests, subscribeToActivity } from '../api/client.js';
import { useT } from '../i18n/LanguageContext.js';

// [GLOBAL LOADING BAR HERE]
// How: A thin animated bar across the very top of the screen appears whenever
//      any request is in flight, and disappears when all have finished.
// Why: Your "loading icon whenever something is processing" requirement. It
//      covers every page and action automatically, including background
//      refreshes, on top of the spinners inside buttons and pages.
/** Shows a progress bar while any API request is running. */
export default function GlobalProgress() {
  const t = useT();
  const busy = useSyncExternalStore(subscribeToActivity, pendingRequests) > 0;
  if (!busy) return null;
  return (
    <LinearProgress
      aria-label={t('Loading')}
      sx={{ position: 'fixed', top: 0, left: 0, right: 0, zIndex: (theme) => theme.zIndex.tooltip + 1, height: 3 }}
    />
  );
}
