import { Card, CardContent, Typography } from '@mui/material';
import PropTypes from 'prop-types';

/** A dashboard number with a caption. */
export default function StatCard({ label, value, caption, color }) {
  return (
    <Card>
      <CardContent>
        <Typography variant="body2" color="text.secondary">{label}</Typography>
        <Typography variant="h4" component="p" color={color || 'text.primary'}>{value}</Typography>
        {caption && <Typography variant="body2" color="text.secondary">{caption}</Typography>}
      </CardContent>
    </Card>
  );
}

StatCard.propTypes = {
  label: PropTypes.node.isRequired,
  value: PropTypes.node,
  caption: PropTypes.node,
  color: PropTypes.string,
};
