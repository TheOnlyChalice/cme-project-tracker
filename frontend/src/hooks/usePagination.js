import { useState } from 'react';

// [ACME: PAGINATION HOOK HERE]
// How: Takes the full list and returns just the rows for the current page,
//      plus the page number, page size, and setters for the paginator. If
//      the list shrinks (for example after filtering), the page is pulled
//      back so it never points past the end.
// Why: With ~1,000 records, admin screens listed dozens of projects and
//      people at once. Showing a page at a time keeps them readable, and one
//      hook gives every list the same behavior.
export default function usePagination(items, initialRowsPerPage = 10) {
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPageState] = useState(initialRowsPerPage);
  const list = items || [];
  const lastPage = Math.max(0, Math.ceil(list.length / rowsPerPage) - 1);
  const current = Math.min(page, lastPage);
  const setRowsPerPage = (next) => {
    setRowsPerPageState(next);
    setPage(0);
  };
  return {
    page: current,
    setPage,
    rowsPerPage,
    setRowsPerPage,
    count: list.length,
    pageItems: list.slice(current * rowsPerPage, current * rowsPerPage + rowsPerPage),
  };
}
