import { Box } from '@mui/material';
import PropTypes from 'prop-types';

// [ACME: BRAND MARK HERE]
// How: ACME's logo: a navy "A" on an amber rounded square, drawn as an SVG so
//      it's sharp at any size. The same shape is the browser tab icon
//      (public/acme.svg).
// Why: A consistent mark in the sidebar, login page, and browser tab makes
//      the app look like a finished product rather than a template.
/** ACME's logo mark. */
export default function BrandMark({ size = 36 }) {
  return (
    <Box component="svg" viewBox="0 0 64 64" aria-hidden="true" sx={{ width: size, height: size, flexShrink: 0 }}>
      <rect width="64" height="64" rx="16" fill="#F5A524" />
      <path d="M20 47 32 15l12 32M24.5 36h15" fill="none" stroke="#081A38" strokeWidth="6"
        strokeLinecap="round" strokeLinejoin="round" />
    </Box>
  );
}

BrandMark.propTypes = {
  size: PropTypes.number,
};
