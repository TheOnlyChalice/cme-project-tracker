import { createContext, useContext } from 'react';

export const ColorModeContext = createContext({ mode: 'light', toggle: () => {} });

/** The current color mode ("light" or "dark") and a function to switch it. */
export const useColorMode = () => useContext(ColorModeContext);
