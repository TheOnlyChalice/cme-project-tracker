# CME Project Tracker API (v1)

Python backend for the CME project tracking platform. Terraform deploys this
folder as a single AWS Lambda function (Python 3.13, `function.handler`).
Locally it runs with a small dev server that calls the same handler.

Data is stored in **PostgreSQL** (Aurora PostgreSQL on AWS). For tests and
quick runs it can also use in-memory storage. The caller is identified with a
temporary `X-User-Id` header until JWT login arrives in the next branch.

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
curl http://localhost:3001/api/v1/health
curl http://localhost:3001/api/v1/insights/at-risk -H "X-User-Id: adm001"
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

## Acting as a user (Phase 1 only)

Send an `X-User-Id` header with a user's ID or username. These users exist
every time the server starts (password `ChangeMe123`, used from Phase 2):

| Username | Role | Reports to | Notes |
| --- | --- | --- | --- |
| `adm001` | admin | - | Can do everything |
| `mgr001` | manager | adm001 | Manages *Customer Portal Redesign* (healthy) |
| `mgr002` | manager | adm001 | Manages *Data Center Migration* (at risk) |
| `emp001` | employee | mgr001 | 30 h booked this week |
| `emp002` | employee | mgr001 | 20 h booked this week |
| `emp003` | employee | mgr002 | Fully booked (40 h) |

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
| `app/auth.py` | Identifies the caller (dev header now, JWT in Phase 2) |
| `app/permissions.py` | Roles and visibility rules |
| `app/audit.py` | Audit log writer and filters |
| `app/clock.py` | Company time zone and Monday-based weeks |
| `app/validation.py`, `app/passwords.py` | Field validation, password hashing |
| `app/seed.py` | Starter users, projects, milestones, and hours |
| `tests/` | Unit tests (`python -m unittest`) |

## Finding added components

Every significant piece of code has a `[COMPONENT HERE]` comment explaining how
it works and why it was built that way:

```bash
grep -rn "HERE]" backend/v1 --include=*.py
```
