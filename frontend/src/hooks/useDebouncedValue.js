import { useEffect, useState } from 'react';

// [SEARCH DEBOUNCE HERE]
// How: Returns the value only after it has stopped changing for 300 ms.
// Why: Typing "migration" would otherwise send nine searches to the API, one
//      per letter; waiting for a pause sends one.
export default function useDebouncedValue(value, delay = 300) {
  const [settled, setSettled] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setSettled(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return settled;
}
