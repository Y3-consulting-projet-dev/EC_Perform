# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository layout

This is a monorepo split into two top-level folders, developed independently:

- `frontend/` — Vue 3 + Vite SPA (all frontend commands run from inside this folder).
- `backend/` — FastAPI + MongoDB API (all backend commands run from inside this folder).

EC Perform is an internal tool for an audit/accounting firm (Y3 Audit & Conseils) to track clients
and audit missions. The UI and API responses are in French.

## Commands

Frontend, run from `frontend/`:

```sh
npm install       # install dependencies
npm run dev       # start Vite dev server with HMR (http://localhost:5173)
npm run build     # production build (output to dist/)
npm run preview   # preview the production build locally
```

There is no lint, test, or type-check script configured. No test framework is installed.

Backend, run from `backend/` with the venv active:

```sh
python app.py     # start the API via uvicorn with reload, on http://127.0.0.1:8000
```

There is no `requirements.txt`-install-only entrypoint beyond `pip install -r requirements.txt`, no
test framework, and no lint config. MongoDB must be running locally (`mongodb://localhost:27017` by
default) before the API will serve anything beyond static errors — `/health` calls
`db.client.server_info()` and will fail loudly if Mongo isn't reachable.

One-off data scripts (run from `backend/` with the venv active):
- `init_db.py` — creates the database by inserting a placeholder doc into a `status` collection.
- `import_personnel.py` — bulk-upserts employees into the `employees` collection from
  `backend/app/data/registre_personnel.csv` (semicolon-delimited, columns `NOM;PRENOMS;GRADE;DEPARTEMENT;Mail`).
  Creates a unique index on `email`.
- `generate_passwords.py` — sets every employee's `password_hash` to the bcrypt hash of a single
  hardcoded default password. Intended as a one-time bootstrap after import, not for routine use.

## Environment configuration

- `backend/.env` (gitignored): `MONGO_URI`, `MONGO_DB_NAME`, `JWT_SECRET_KEY`. `app/core/security.py`
  reads `JWT_SECRET_KEY` with `os.environ[...]` (not `.get`), so the process will hard-fail at import
  time if it's unset.
- `frontend/.env`: `VITE_API_URL` (defaults to `http://localhost:8000` in code if unset).

## Architecture

### Backend (`backend/app/`)

Layered FastAPI app — routers (controllers) → services (business logic) → Mongo, plus Pydantic
request models:

- `db/session.py` — module-level `pymongo.MongoClient` instance (`db`). No repository/DAO layer;
  services call `db.<collection>.find_one(...)` etc. directly.
- `core/security.py` — bcrypt password hashing and JWT creation/decoding (HS256, 8h expiry, `sub`
  claim = email).
- `core/deps.py` — the `get_current_employee` dependency, which decodes the bearer token, re-fetches
  the employee document from Mongo on every request (no in-memory session), and 401s if either the
  token or the lookup fails.
- `models/` — Pydantic request schemas, one module per domain (`auth.py`, `employee.py`, `client.py`,
  `mission.py`, `document.py`).
- `services/` — business logic and Mongo access, one module per domain (`employee_service.py`,
  `client_service.py`, `mission_service.py`, `document_service.py`, `balance_service.py`), plus
  `balance_engine.py` (pure functions, no FastAPI/Mongo dependency: parses balance `.xlsx` files and
  computes the intangibilité/cohérence/vraisemblance SYSCOHADA checks).
- `routers/` — one `APIRouter` per domain (`auth.py`, `employees.py`, `clients.py`, `missions.py`,
  `documents.py` — which also serves `/uploads/{mission_id}/{stored_name}`, `balances.py`), all
  included in `main.py`, which only builds the `FastAPI` app, wires CORS, and exposes `/health`.

Auth model: login issues a JWT keyed on email; the frontend stores the raw token and the employee
object in `localStorage` and sends `Authorization: Bearer <token>` on subsequent requests. There is
no refresh-token flow — the token simply expires after 8 hours and the user must log in again.

The `employees` collection (populated via `import_personnel.py`) is the only real data store in use;
routes for clients/missions seen in the frontend (`Clients.vue`, `Home.vue` stats) are still
frontend-only mock data with no corresponding backend collection or endpoints yet.

CORS is hardcoded to allow only `http://localhost:5173` (`main.py`) — update this if the frontend
dev port or a deployed origin changes.

### Frontend (`frontend/src/`)

- `router/index.js` — the only source of truth for auth gating. A global `beforeEach` guard checks
  `localStorage.getItem('access_token')` and redirects to `/login` when absent (or away from
  `/login` when present) — there's no Pinia/auth store; auth state is read straight from
  `localStorage` wherever it's needed (`AppShell.vue`, `Profile.vue`, `login.vue` all do this
  independently rather than through a shared composable).
- `layouts/AppShell.vue` — the shell (header + sidebar nav) wrapping all authenticated routes except
  `/profil`, which renders its own full-page header instead of going through `AppShell`.
- `views/` — route-level pages (`login.vue`, `Home.vue` dashboard, `Clients.vue`, `Profile.vue`).
  Views call `fetch` directly against `VITE_API_URL` inline (see `login.vue`, `Profile.vue`) — there
  is no shared API client/wrapper yet, so new endpoints currently mean copy-pasting the same
  `fetch`/`authHeaders()` pattern.
- `composables/`, `stores/`, `plugins/`, `utils/` exist as empty directories, representing intended
  future structure (e.g. a shared API client, an auth composable/store) but nothing is wired up yet.
- Tailwind CSS 4 via `@tailwindcss/vite` — no separate `tailwind.config.js`; configuration is
  CSS-first (see `src/assets/main.css` / `base.css`).
- Plain JavaScript, not TypeScript. `jsconfig.json` declares the `@/*` → `./src/*` path alias for
  editor tooling, but `vite.config.js` does not register a matching `resolve.alias` — `@/` imports
  will not resolve at dev/build time until that's added; all current imports use relative paths.
- Entry point: `index.html` → `src/main.js` → mounts `App.vue` (just a `RouterView`) to `#app`.
