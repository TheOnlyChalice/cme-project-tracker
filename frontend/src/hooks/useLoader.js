import { useCallback, useEffect, useState } from 'react';

// [ACME: DATA LOADER HOOK HERE]
// How: Runs an async load function and returns { data, loading, error,
//      reload }. Each load is tagged with a key built from its inputs; the
//      result is only kept if it belongs to the latest key, and "loading" is
//      true until the latest key's result arrives.
// Why: Every page loads data the same way, so one hook keeps spinners and
//      error messages consistent. Tagging results stops a slow, outdated
//      request (e.g. after switching weeks quickly) overwriting newer data,
//      and the previous data stays on screen while reloading, so pages don't
//      flash empty.
export default function useLoader(load, deps = []) {
  const [version, setVersion] = useState(0);
  const key = JSON.stringify([...deps, version]);
  const [state, setState] = useState({ key: null, data: null, error: null });

  useEffect(() => {
    let current = true;
    load()
      .then((data) => current && setState({ key, data, error: null }))
      .catch((error) => current && setState({ key, data: null, error }));
    return () => {
      current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const reload = useCallback(() => setVersion((v) => v + 1), []);
  return { data: state.data, error: state.error, loading: state.key !== key, reload };
}
