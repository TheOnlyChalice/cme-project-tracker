# CME Project Tracker API (v1)

Python backend for the CME project tracking platform. Terraform deploys this
folder as a single AWS Lambda function (Python 3.13, `function.handler`).
Locally it runs with a small dev server that calls the same handler.

Data is stored in **PostgreSQL** (Aurora PostgreSQL on AWS). For tests and
quick runs it can also use in-memory storage. Users sign in with a username
(or email) and password and receive a **JWT**, which they send with every
request as `Authorization: Bearer <token>`.

## Storage

| Where | Backend | How it's chosen |
| --- | --- | --- |
| AWS Lambda | Aurora PostgreSQL | The workshop injects `POSTGRES_*` settings, so PostgreSQL is used automatically |
| Your PC with `.env` | Local PostgreSQL | `STORE_BACKEND=postgres` in `backend/v1/.env` |
| Your PC without `.env`, and unit tests | Memory | Default when no database is configured |

On first start against an empty database, the API creates its tables
(`app/storage/schema.sql`) and adds the starter data. After that, data persists.
`GET /health` shows which storage is in use and whether the database answers.

## Set up PostgreSQL on Windows (one time)

1. Install PostgreSQL 17 from https://www.postgresql.org/download/windows/
   (the EDB installer). Keep port 5432, set a password for the `postgres`
   user, and skip Stack Builder at the end.
2. Create two databases, one for the app and one the tests can wipe
   (Git Bash; enter your password when asked):

   ```bash
   "/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -c "CREATE DATABASE cme;"
   "/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -c "CREATE DATABASE cme_test;"
   ```

3. Copy `backend/v1/.env.sample` to `backend/v1/.env` and put your password in it.

## Run locally (Git Bash on Windows)

```bash
pip install -r backend/v1/requirements.txt   # psycopg (PostgreSQL) and tzdata (time zones)
python backend/v1/dev_server.py
```

It prints `Storage: postgres` (or `memory` without a `.env`). The API is now at
`http://localhost:3001/api/v1`. In a second terminal:

```bash
curl -s http://localhost:3001/api/v1/health

# Sign in and keep the access token in a variable
TOKEN=$(curl -s -X POST http://localhost:3001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"adm001","password":"ChangeMe123"}' \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

curl -s http://localhost:3001/api/v1/insights/at-risk -H "Authorization: Bearer $TOKEN"
```

## Run the tests

In memory (fast, no database needed):

```bash
cd backend/v1
python -m unittest -v
```

Against PostgreSQL (the same tests, on the real database). The database name
must end in `_test`, because every test empties all tables first:

```bash
cd backend/v1
STORE_BACKEND=postgres POSTGRES_HOST=localhost POSTGRES_USER=postgres \
POSTGRES_PASS=your-password POSTGRES_NAME=cme_test python -m unittest -v
```

To measure coverage, install the `coverage` package and run
`coverage run -m unittest && coverage report`.

## Signing in

| Endpoint | Body | Returns |
| --- | --- | --- |
| `POST /auth/login` | `{"username": "...", "password": "..."}` (username or email) | `access_token`, `refresh_token`, `expires_in`, `user` |
| `POST /auth/refresh` | `{"refresh_token": "..."}` | A new token pair |
| `POST /auth/logout` | (send the access token) | Signs out on every device |

- Access tokens last 60 minutes (`ACCESS_TOKEN_MINUTES`); refresh tokens last
  7 days (`REFRESH_TOKEN_DAYS`). A `token_expired` error means "refresh".
- Tokens are signed with `JWT_SECRET`. On AWS, Terraform generates it
  (`infra/jwt.tf`); locally, set it in `backend/v1/.env`.
- Logging out, changing a password, a role change, or being archived signs the
  user out everywhere (`token_revoked`).
- Changing your own password requires `current_password`.
- Five wrong passwords in a row lock the account for 15 minutes (`429 account_locked`).
  An admin setting a new password unlocks it.
- The user's role is always read from the database, so role changes apply immediately.

These starter users exist when the database is first created. They all use the
password `ChangeMe123` (set `DEV_SEED_PASSWORD` to change it before first start):

| Username | Role | Reports to | Notes |
| --- | --- | --- | --- |
| `adm001` | admin | - | Can do everything |
| `mgr001` | manager | - | Customer Portal Redesign, Mobile App Launch |
| `mgr002` | manager | - | Data Center Migration (at risk), Onboarding Revamp (no milestones) |
| `mgr003` | manager | - | Security Compliance Audit, Analytics Dashboard (going inactive) |
| `emp001` | employee | mgr001 | Split across two projects, fully booked |
| `emp002` | employee | mgr001 | |
| `emp003` | employee | mgr002 | Fully booked (40 h) |
| `emp004` | employee | mgr001 | Mobile App Launch |
| `emp005` | employee | mgr002 | Free this week |
| `emp006` | employee | mgr003 | Security audit |
| `emp007` | employee | mgr003 | Security audit |
| `emp008` | employee | mgr003 | Free this week |

Admins can also see one completed project (Legacy CRM Retirement) and one
abandoned project (Office Kiosk Pilot). Missing demo records are added on start
without changing anything that already exists. Only employees have a manager.

With PostgreSQL, data persists across restarts. With in-memory storage, it
resets to the starter data every time the server starts.

## Business rules

- **Roles:** Admin inherits Manager, which inherits Employee.
- **Teams:** a manager's team is the employees whose `manager_id` points to them.
- **Visibility:** employees see their manager's active projects; managers see the
  active projects they manage; only admins see completed, abandoned, or archived work.
- **Hours:** every employee has 40 hours per week, starting fresh at 12:00 AM
  Monday (Eastern, set by `COMPANY_TIMEZONE`). Managers assign hours to milestones
  for their own team. Neither the 40-hour cap nor the project's `allocated_hours`
  can be exceeded. Past weeks are locked.
- **Cost:** labor cost = hours x (salary / 2,080). Compared against the project budget.
- **Soft deletes:** nothing is deleted; items are archived and only admins restore them.
- **Audit log:** every change is recorded; only admins can read it; entries can't
  be edited or deleted (enforced in Python and by a database trigger). Password
  hashes are never logged.
- **Inactivity:** a project with no activity (no change to it, its milestones,
  or its hours) for 10 days, and no hours booked from the current week on,
  carries an `inactive` risk flag. Nothing is archived automatically; an admin
  can archive projects idle for 14+ days with `POST /admin/maintenance`.
- **Two audit logs:** `GET /audit-log` shows account activity only (people
  created, edited, promoted, moved, archived). `GET /projects/{id}/audit-log`
  shows everything about one project, its milestones, and its hours. Both are
  admin-only, and neither ever rewrites an entry.
- **Budgets are admin-only:** managers can see a project's budget and how much
  is used, but only admins can set or change it.
- **Error format:** every error is `{"error": {"status", "code", "message", "details"}}`.
- **Speed:** within a request, each table is read once and served from memory
  afterwards (`app/storage/cache.py`), so reports stay fast with ~1,000 records.
- **Bulk demo data:** about 1,000 records (`app/seed_bulk.py`) are added on
  start; set `DEMO_BULK_DATA=false` to skip them.
- **Date cascades:** when a milestone's end date moves, `PATCH /milestones/{id}`
  with `"shift_following": true` moves every later open milestone by the same
  number of days; when a project's start moves, `PATCH /projects/{id}` with
  `"shift_milestones": true` moves all open milestones. Completed milestones
  never move. Running past the project's end is refused unless
  `"extend_project": true` is sent. Future hours that no longer fit are released.
- **Finishing a project:** completing the last open milestone completes and
  archives the project. Only admins archive milestones.
- **Translatable messages:** every risk flag includes `params` (its numbers) and
  lockout errors include `details.minutes`, so the frontend can show them in
  Spanish as well as English.
- **Transactions:** each request is all-or-nothing. If any step fails, nothing
  it wrote is kept.
- **At risk:** a project is flagged if it's past its end date, has an overdue
  milestone, ends within 14 days with open milestones, is more than 25 points
  behind schedule, has no milestones after starting, is forecast over budget, or
  has 90%+ of its hours assigned. Each flag comes with a reason.

## Endpoints

All paths are under `/api/v1`. Errors always look like
`{"error": {"code": "...", "message": "...", "details": {...}}}`.

| Method | Path | Who |
| --- | --- | --- |
| GET | `/health`, `/` | anyone |
| POST | `/auth/login`, `/auth/refresh` | anyone |
| POST | `/auth/logout` | any signed-in user |
| GET | `/me` | any user |
| GET | `/users?role=&manager_id=&search=&include_archived=` | any user (filtered by role) |
| POST | `/users` | admin |
| GET / PATCH | `/users/{id}` | visible users / self (personal details) or admin |
| DELETE | `/users/{id}` (archive) | admin |
| POST | `/users/{id}/restore` | admin |
| GET | `/users/{id}/team` | that manager, admin |
| GET | `/users/{id}/availability?week=` | users who can see that user |
| GET | `/projects?status=&manager_id=&search=&include_archived=` | any user (filtered by role) |
| POST | `/projects` | admin |
| GET / PATCH | `/projects/{id}` | visible / project manager or admin |
| DELETE | `/projects/{id}` (archive) | admin |
| POST | `/projects/{id}/complete` | project manager, admin |
| POST | `/projects/{id}/abandon`, `/projects/{id}/restore` | admin |
| GET | `/projects/{id}/health`, `/projects/{id}/milestone-chain` | visible |
| GET / POST | `/projects/{id}/milestones` | visible / project manager or admin |
| GET / PATCH / DELETE | `/milestones/{id}` | visible / project manager or admin |
| POST | `/milestones/{id}/complete` | project manager, admin |
| POST | `/milestones/{id}/restore` | admin |
| GET / POST | `/hour-assignments?user_id=&project_id=&milestone_id=&week=` | filtered by role / project manager or admin |
| PATCH / DELETE | `/hour-assignments/{id}` | project manager, admin |
| GET | `/insights/projects?at_risk=&include_closed=` | any user (filtered by role) |
| GET | `/insights/at-risk` | any user (filtered by role) |
| GET | `/insights/utilization?week=` | any user (filtered by role) |
| GET | `/search?q=` | any user (only finds what they may see) |
| GET | `/insights/timeline` | any user (filtered by role) |
| GET | `/projects/{id}/cost-series` | managers and admins who can see the project |
| GET | `/insights/capacity?start=&weeks=` | any user (filtered by role) |
| POST | `/admin/maintenance` | admin |
| GET | `/projects/{id}/audit-log?actor_id=&action=&entity_type=&from=&to=&limit=&offset=` | admin |
| GET | `/audit-log?actor_id=&action=&entity_type=&entity_id=&from=&to=&limit=&offset=` | admin |

## Structure

| Path | Purpose |
| --- | --- |
| `function.py` | Lambda entry point (`handler`) |
| `dev_server.py` | Local server that calls the same handler |
| `app/router.py`, `app/request.py`, `app/responses.py` | Routing, request parsing, JSON responses |
| `app/routes/` | HTTP routes, one module per domain |
| `app/services/` | Business rules, one module per domain |
| `app/store.py` | Picks the storage backend at startup |
| `app/storage/postgres.py` | PostgreSQL storage (psycopg 3) |
| `app/storage/memory.py` | In-memory storage for tests and quick runs |
| `app/storage/schema.sql` | Tables, constraints, indexes, audit trigger |
| `app/auth.py` | Identifies the caller from their Bearer token |
| `app/tokens.py` | Creates and checks JWTs |
| `app/services/auth.py` | Login, refresh, logout, lockout |
| `app/permissions.py` | Roles and visibility rules |
| `app/audit.py` | Audit log writer and filters |
| `app/clock.py` | Company time zone and Monday-based weeks |
| `app/validation.py`, `app/passwords.py` | Field validation, password hashing |
| `app/seed.py` | Starter users, projects, milestones, and hours |
| `tests/` | Unit tests (`python -m unittest`) |

## Finding added components

In VS Code, press **Ctrl+Shift+F** and search for `[ACME:` to list every tagged
component across the project. From a terminal:

Every significant piece of code has a `[ACME: COMPONENT HERE]` comment explaining how
it works and why it was built that way:

```bash
grep -rn "\[ACME:" backend/v1 --include=*.py
```
