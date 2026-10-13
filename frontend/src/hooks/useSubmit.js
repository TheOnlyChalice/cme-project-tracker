import { useCallback, useState } from 'react';

// [FORM SUBMIT HOOK HERE]
// How: Wraps a save function with busy and error state; returns true when it
//      succeeded so the form can close.
// Why: Every form needs the same "disable while saving, show what went
//      wrong" behavior; the backend's per-field errors flow straight into the
//      matching inputs via fieldError().
export default function useSubmit() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const run = useCallback(async (action) => {
    setBusy(true);
    setError(null);
    try {
      await action();
      return true;
    } catch (err) {
      setError(err);
      return false;
    } finally {
      setBusy(false);
    }
  }, []);

  const reset = useCallback(() => setError(null), []);
  return { busy, error, run, reset };
}
