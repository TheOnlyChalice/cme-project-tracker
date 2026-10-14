# ACME Project Tracker – Frontend

React 19 + Vite app using **Material UI** components and **React Responsive**
for layout changes on small screens. It talks to the Python API in
`backend/v1` using JWT sign-in.

## Design: "navy command center"

ACME navy and white with a single amber accent (used only for "look here":
today, the current item, risk, key actions), Space Grotesk headings over IBM
Plex Sans body text, a navy sidebar with the ACME mark, and a white work area.

- **Dashboard:** a navy welcome banner with four headline numbers, the
  **portfolio timeline** (every project as a lane of milestone bars against an
  amber "today" line, Months / Quarters zoom), "Needs attention" with each
  risk's reason, this week's capacity, and the project health table.
- **Hours:** a **capacity heat map** (people by week, shaded by how full each
  40-hour week is; click a week to see and edit its bookings). Employees see
  their own six-week strip.
- **Project page:** the same timeline for the project's own milestones.
- **Login:** split screen with the brand panel beside the sign-in card.
- **Top bar:** project search (Ctrl+K), language, and light/dark mode.

## Features

- **Light and dark mode:** ACME dark blue and white in both; follows the
  computer's setting until you pick one with the sun/moon button (top bar and
  login page); the choice is remembered.
- **Collapsible sidebar:** the arrow at the bottom of the sidebar slides it
  down to an icon-only rail (labels show as tooltips); remembered per browser.
- **English and Spanish:** the EN | ES switch translates every screen,
  including backend error messages and risk flags, plus date and money formats.
  Translations live in `src/i18n/es.js`.
- **Loading feedback:** a progress bar runs across the top of the screen
  whenever any request is in flight, and buttons show a spinner while their
  action runs (and can't be double-clicked).
- **Role-based screens:** menus, pages, and buttons only appear for roles that
  can use them; the backend enforces the same rules on every request.

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
| `src/theme/` | Material UI theme for light and dark mode |
| `src/i18n/` | Language switch, translation lookup, Spanish dictionary |
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
