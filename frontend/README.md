# ACME Project Tracker – Frontend

React 19 + Vite app using **Material UI** components and **React Responsive**
for layout changes on small screens. It talks to the Python API in
`backend/v1` using JWT sign-in.

## Run locally (Git Bash on Windows)

You need Node.js 20.19 or newer (`node --version`) and the backend running.

```bash
# Window 1: the API
python backend/v1/dev_server.py

# Window 2: the website
cd frontend
cp .env.sample .env.local      # VITE_API_URL=http://localhost:3001
npm install
npm run dev
```

Open http://localhost:3000 and sign in, for example as `adm001`, `mgr001`, or
`emp001` (password `ChangeMe123` for the starter accounts).

## Deploy (on the WorkSpace)

```bash
cd frontend && npm install && cd ..
./bin/deploy-frontend.sh
```

The script builds with `VITE_API_URL` set to your CloudFront address and
uploads the site to S3. The site and API share that address.

## Pages

| Page | Who | What it does |
| --- | --- | --- |
| Dashboard | everyone | Headline numbers, at-risk projects with reasons, project health |
| Projects | everyone (filtered by role) | Search and filter; admins create projects |
| Project detail | everyone who can see it | Health, milestone chain, booked hours; managers edit, complete, add milestones, assign hours; admins abandon, archive, restore |
| Hours | managers/admins: team planner; employees: my week | Weekly 40-hour capacity and bookings |
| People | managers (their team), admins (everyone) | Admins create, edit, archive, restore people |
| Audit log | admins | Filterable, read-only history of every change |
| My profile | everyone | Edit own details, change password |

## Structure

| Path | Purpose |
| --- | --- |
| `src/main.jsx` | Theme, router, error boundary, providers |
| `src/App.jsx` | Every page and the role it needs |
| `src/theme.js` | Material UI theme (colors, fonts, defaults) |
| `src/api/` | API client (tokens, refresh, errors) and session storage |
| `src/auth/` | Sign-in state and route guard |
| `src/components/` | Shared pieces: layout, dialogs, chips, cards |
| `src/components/forms/` | Create/edit forms for projects, milestones, hours, people |
| `src/pages/` | One file per page |
| `src/hooks/` | Data loading, form submit, debounce, screen size |
| `src/utils/` | Formatting and role helpers |

Addresses use `#` (for example `/#/projects/123`) so refreshing any page works
when the site is served from S3 behind CloudFront.

## Finding added components

```bash
grep -rn "HERE]" frontend/src
```
