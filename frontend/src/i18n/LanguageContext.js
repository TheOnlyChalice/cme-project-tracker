import { createContext, useContext } from 'react';

export const LanguageContext = createContext({ lang: 'en', setLang: () => {}, t: (text) => text });

/** The current language and a function to change it. */
export const useLanguage = () => useContext(LanguageContext);

/** The translate function: t('English text', { name: 'value' }). */
export const useT = () => useContext(LanguageContext).t;
