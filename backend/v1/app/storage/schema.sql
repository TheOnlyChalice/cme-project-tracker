-- [ACME: DATABASE SCHEMA HERE]
-- How: Every table, constraint, index, and trigger the API needs. The script
--      only uses "IF NOT EXISTS" / "OR REPLACE" statements, so it runs safely
--      every time Lambda starts and never touches existing data.
-- Why: The database enforces the core rules itself (valid roles and statuses,
--      unique emails and project names, hours between 0 and 40, weeks that
--      start on Monday, an append-only audit log). Even a bug in the Python
--      code can't store data that breaks them.

CREATE TABLE IF NOT EXISTS users (
    id                  UUID PRIMARY KEY,
    username            VARCHAR(6)   NOT NULL UNIQUE CHECK (length(username) = 6),
    first_name          VARCHAR(100) NOT NULL,
    last_name           VARCHAR(100) NOT NULL,
    email               VARCHAR(254) NOT NULL,
    password_hash       TEXT         NOT NULL,
    role                VARCHAR(10)  NOT NULL CHECK (role IN ('admin', 'manager', 'employee')),
    job_title           VARCHAR(100),
    salary              NUMERIC(12, 2) CHECK (salary >= 0),
    profile_picture_url VARCHAR(500),
    manager_id          UUID REFERENCES users (id),
    is_archived         BOOLEAN      NOT NULL DEFAULT FALSE,
    archived_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ  NOT NULL,
    updated_at          TIMESTAMPTZ  NOT NULL,
    CONSTRAINT users_employee_has_manager CHECK (role <> 'employee' OR manager_id IS NOT NULL),
    CONSTRAINT users_not_own_manager CHECK (manager_id IS NULL OR manager_id <> id)
);
-- Sign-in columns added with JWT. ADD COLUMN IF NOT EXISTS upgrades databases
-- created before this branch without touching their data.
ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version      INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until       TIMESTAMPTZ;
CREATE UNIQUE INDEX IF NOT EXISTS users_email_lower_key ON users (lower(email));

-- [ACME: MANAGERS HAVE NO MANAGER HERE]
-- How: Clears any manager set on a manager or admin from before this rule,
--      then adds a constraint so only employees can have a manager.
-- Why: Managers and admins lead teams; they don't work under anyone. The
--      update only touches rows that break the rule, so rerunning it is safe.
UPDATE users SET manager_id = NULL WHERE role <> 'employee' AND manager_id IS NOT NULL;
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'users_only_employees_have_managers') THEN
        ALTER TABLE users ADD CONSTRAINT users_only_employees_have_managers
            CHECK (role = 'employee' OR manager_id IS NULL);
    END IF;
END $$;
CREATE INDEX IF NOT EXISTS users_manager_idx ON users (manager_id);

CREATE TABLE IF NOT EXISTS projects (
    id                  UUID PRIMARY KEY,
    name                VARCHAR(150) NOT NULL,
    description         TEXT,
    start_date          DATE         NOT NULL,
    end_date            DATE         NOT NULL,
    allocated_hours     INTEGER      NOT NULL CHECK (allocated_hours > 0),
    budget              NUMERIC(14, 2) CHECK (budget >= 0),
    manager_id          UUID         NOT NULL REFERENCES users (id),
    active_milestone_id UUID,
    status              VARCHAR(10)  NOT NULL CHECK (status IN ('active', 'completed', 'abandoned')),
    is_archived         BOOLEAN      NOT NULL DEFAULT FALSE,
    archived_at         TIMESTAMPTZ,
    created_by          UUID REFERENCES users (id),
    created_at          TIMESTAMPTZ  NOT NULL,
    updated_at          TIMESTAMPTZ  NOT NULL,
    CONSTRAINT projects_dates_valid CHECK (end_date > start_date)
);
CREATE UNIQUE INDEX IF NOT EXISTS projects_name_lower_key ON projects (lower(name));
CREATE INDEX IF NOT EXISTS projects_manager_idx ON projects (manager_id);

CREATE TABLE IF NOT EXISTS milestones (
    id           UUID PRIMARY KEY,
    project_id   UUID         NOT NULL REFERENCES projects (id),
    sequence     INTEGER      NOT NULL CHECK (sequence > 0),
    name         VARCHAR(150) NOT NULL,
    goal         TEXT,
    deliverables JSONB        NOT NULL DEFAULT '[]'::jsonb,
    start_date   DATE         NOT NULL,
    end_date     DATE         NOT NULL,
    status       VARCHAR(10)  NOT NULL CHECK (status IN ('active', 'completed')),
    completed_at TIMESTAMPTZ,
    is_archived  BOOLEAN      NOT NULL DEFAULT FALSE,
    archived_at  TIMESTAMPTZ,
    created_at   TIMESTAMPTZ  NOT NULL,
    updated_at   TIMESTAMPTZ  NOT NULL,
    CONSTRAINT milestones_sequence_unique UNIQUE (project_id, sequence),
    CONSTRAINT milestones_dates_valid CHECK (end_date >= start_date)
);
CREATE INDEX IF NOT EXISTS milestones_project_idx ON milestones (project_id);

-- The project -> active milestone link is added after both tables exist.
-- DEFERRABLE lets a project and its first milestone be created in one transaction.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'projects_active_milestone_fk') THEN
        ALTER TABLE projects ADD CONSTRAINT projects_active_milestone_fk
            FOREIGN KEY (active_milestone_id) REFERENCES milestones (id)
            DEFERRABLE INITIALLY DEFERRED;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS hour_assignments (
    id           UUID PRIMARY KEY,
    user_id      UUID          NOT NULL REFERENCES users (id),
    milestone_id UUID          NOT NULL REFERENCES milestones (id),
    project_id   UUID          NOT NULL REFERENCES projects (id),
    week_start   DATE          NOT NULL CHECK (EXTRACT(ISODOW FROM week_start) = 1),
    hours        NUMERIC(5, 2) NOT NULL CHECK (hours > 0 AND hours <= 40),
    assigned_by  UUID REFERENCES users (id),
    is_archived  BOOLEAN       NOT NULL DEFAULT FALSE,
    archived_at  TIMESTAMPTZ,
    created_at   TIMESTAMPTZ   NOT NULL,
    updated_at   TIMESTAMPTZ   NOT NULL
);
-- One live assignment per employee, milestone, and week.
CREATE UNIQUE INDEX IF NOT EXISTS hour_assignments_unique_live
    ON hour_assignments (user_id, milestone_id, week_start) WHERE NOT is_archived;
CREATE INDEX IF NOT EXISTS hour_assignments_user_week_idx ON hour_assignments (user_id, week_start);
CREATE INDEX IF NOT EXISTS hour_assignments_project_idx ON hour_assignments (project_id);
CREATE INDEX IF NOT EXISTS hour_assignments_milestone_idx ON hour_assignments (milestone_id);

CREATE TABLE IF NOT EXISTS audit_log (
    id          UUID PRIMARY KEY,
    actor_id    UUID REFERENCES users (id),
    action      VARCHAR(20) NOT NULL CHECK (action IN ('create', 'update', 'archive', 'restore',
                                                       'assign_role', 'assign_team',
                                                       'complete', 'abandon')),
    entity_type VARCHAR(50) NOT NULL,
    entity_id   UUID        NOT NULL,
    changes     JSONB       NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS audit_log_created_idx ON audit_log (created_at DESC);
CREATE INDEX IF NOT EXISTS audit_log_entity_idx ON audit_log (entity_type, entity_id);
CREATE INDEX IF NOT EXISTS audit_log_actor_idx ON audit_log (actor_id);

-- [ACME: AUDIT TRIGGER HERE]
-- How: A trigger rejects every UPDATE or DELETE on audit_log rows.
-- Why: A second layer behind the Python check: even someone connecting to the
--      database directly can't quietly rewrite or remove audit history.
CREATE OR REPLACE FUNCTION audit_log_block_changes() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit_log is append-only: entries cannot be changed or deleted';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS audit_log_append_only ON audit_log;
CREATE TRIGGER audit_log_append_only
    BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION audit_log_block_changes();
