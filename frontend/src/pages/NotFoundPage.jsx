import { Box, Button, Typography } from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';

/** Shown for addresses that don't match any page. */
export default function NotFoundPage() {
  return (
    <Box sx={{ textAlign: 'center', py: 8 }}>
      <Typography variant="h4" component="h1" gutterBottom>Page not found</Typography>
      <Typography color="text.secondary" sx={{ mb: 3 }}>
        It may have been moved, archived, or you may not have access to it.
      </Typography>
      <Button variant="contained" component={RouterLink} to="/">Back to dashboard</Button>
    </Box>
  );
}
