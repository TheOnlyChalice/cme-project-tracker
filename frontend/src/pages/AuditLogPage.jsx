import AuditLogTable from '../components/AuditLogTable.jsx';
import PageHeader from '../components/PageHeader.jsx';
import { useT } from '../i18n/LanguageContext.js';

// [ACME: GENERAL AUDIT PAGE HERE]
// How: The audit log in the sidebar shows account activity only: people
//      created, edited, promoted, moved to another manager, archived, or
//      restored. Project, milestone, and hours activity is in each project's
//      own audit log instead.
// Why: Your rule: the general log is for company-wide account changes, so
//      admins aren't searching through thousands of project edits to find
//      who changed someone's role.
/** Admin-only, read-only history of account changes. */
export default function AuditLogPage() {
  const t = useT();
  return (
    <>
      <PageHeader title={t('Audit log')}
        subtitle={t("Account activity: who was created, changed, or archived, by whom, and when. Project activity is in each project's own audit log.")} />
      <AuditLogTable path="/audit-log" itemTypes={['user']} itemName={(entry, names) => names[entry.entity_id] || ''} />
    </>
  );
}
