import { useMediaQuery } from 'react-responsive';

// [REACT RESPONSIVE HERE]
// How: react-responsive's useMediaQuery reports whether the screen is narrower
//      than 900px (Material UI's "md" breakpoint).
// Why: The brief asks for React Responsive. Pages use this to switch layouts,
//      such as a slide-out menu instead of a fixed sidebar, and stacked cards
//      instead of wide tables on phones.
export default function useIsMobile() {
  return useMediaQuery({ maxWidth: 899 });
}
