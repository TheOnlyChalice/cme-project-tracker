import { createContext, useContext } from 'react';

export const NotifyContext = createContext(() => {});

/** Show a short success message at the bottom of the screen. */
export const useNotify = () => useContext(NotifyContext);
