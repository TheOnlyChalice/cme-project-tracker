import PropTypes from 'prop-types';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { setFormatLocale } from '../utils/format.js';
import { LanguageContext } from './LanguageContext.js';
import { translate } from './translate.js';

const KEY = 'acme.language';
const LOCALES = { en: 'en-US', es: 'es-ES' };

function initialLanguage() {
  const saved = localStorage.getItem(KEY);
  if (saved && LOCALES[saved]) return saved;
  return navigator.language?.toLowerCase().startsWith('es') ? 'es' : 'en';
}

// [LANGUAGE PROVIDER HERE]
// How: Holds the chosen language (English or Spanish), remembers it in the
//      browser, starts in Spanish if the browser is set to Spanish, and
//      updates the page's lang attribute and the date/number format.
// Why: One switch translates the whole app instantly, including dates
//      ("13 oct 2026") and money, and screen readers pronounce text in the
//      right language because of the lang attribute.
export default function LanguageProvider({ children }) {
  const [lang, setLangState] = useState(initialLanguage);
  setFormatLocale(LOCALES[lang]);

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const setLang = useCallback((next) => {
    localStorage.setItem(KEY, next);
    setLangState(next);
  }, []);

  const value = useMemo(() => ({
    lang,
    setLang,
    t: (text, vars) => translate(lang, text, vars),
  }), [lang, setLang]);

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

LanguageProvider.propTypes = {
  children: PropTypes.node,
};
