import { TablePagination } from '@mui/material';
import PropTypes from 'prop-types';
import { useT } from '../i18n/LanguageContext.js';

/** Translated page controls for a list paged with usePagination. */
export default function Paginator({ pager, options = [10, 25, 50], label = 'Rows per page:' }) {
  const t = useT();
  if (pager.count <= Math.min(...options)) return null;
  return (
    <TablePagination
      component="div"
      count={pager.count}
      page={pager.page}
      onPageChange={(_, next) => pager.setPage(next)}
      rowsPerPage={pager.rowsPerPage}
      onRowsPerPageChange={(event) => pager.setRowsPerPage(Number(event.target.value))}
      rowsPerPageOptions={options}
      labelRowsPerPage={t(label)}
      labelDisplayedRows={({ from, to, count }) => t('{from}–{to} of {count}', { from, to, count })}
      sx={{ borderTop: 0 }}
    />
  );
}

Paginator.propTypes = {
  pager: PropTypes.shape({
    count: PropTypes.number.isRequired,
    page: PropTypes.number.isRequired,
    setPage: PropTypes.func.isRequired,
    rowsPerPage: PropTypes.number.isRequired,
    setRowsPerPage: PropTypes.func.isRequired,
  }).isRequired,
  options: PropTypes.arrayOf(PropTypes.number),
  label: PropTypes.string,
};
