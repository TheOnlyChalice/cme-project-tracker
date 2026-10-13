import { Box, Typography } from '@mui/material';
import PropTypes from 'prop-types';

/** Page title with an optional subtitle and action buttons on the right. */
export default function PageHeader({ title, subtitle, actions }) {
  return (
    <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 2, mb: 3 }}>
      <Box sx={{ flexGrow: 1, minWidth: 220 }}>
        <Typography variant="h5" component="h1">{title}</Typography>
        {subtitle && <Typography color="text.secondary">{subtitle}</Typography>}
      </Box>
      {actions && <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>{actions}</Box>}
    </Box>
  );
}

PageHeader.propTypes = {
  title: PropTypes.node.isRequired,
  subtitle: PropTypes.node,
  actions: PropTypes.node,
};
