# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository layout

This is a monorepo split into two top-level folders:

- `frontend/` — the Vue 3 + Vite app (all commands below are run from inside this folder).
- `backend/` — currently contains only an empty `venv/` (Python virtual environment); no backend
  source code exists yet.

## Project state

`frontend/` is a freshly scaffolded Vue 3 + Vite project (via `create-vue`). There is no application
functionality implemented yet:

- `frontend/src/components`, `composables`, `layouts`, `plugins`, `router`, `stores`, `utils`, and
  `views` all exist but are currently empty directories — they represent the intended structure for
  a future app (router-based views, Pinia-style stores, composables, etc.) but nothing is wired up
  yet. Neither `vue-router` nor `pinia` (or any state/routing library) is installed in `package.json`.
- `frontend/src/App.vue` currently imports `./components/HelloWorld.vue` and
  `./components/TheWelcome.vue`, which do not exist in `src/components` — the default `create-vue`
  starter components were removed without updating `App.vue`. Additionally, `App.vue` itself is
  currently an empty (0-byte) file on disk. Expect the dev server to fail until this is resolved.

Because of this, do not assume architecture beyond what's described below — there are no existing
patterns to follow yet for routing, state management, or API calls. When implementing new structure,
it's reasonable to use the empty directories per their evident intent (`router/` for Vue Router,
`stores/` for state, `views/` for route-level components, `composables/` for shared reactive logic).

## Commands

Run from `frontend/`:

```sh
npm install       # install dependencies
npm run dev       # start Vite dev server with HMR
npm run build     # production build (output to dist/)
npm run preview   # preview the production build locally
```

There is no lint, test, or type-check script configured in `package.json`. No test framework
(Vitest, Cypress, Playwright) is installed.

## Stack

- **Vue 3** (`<script setup>` SFCs), built with **Vite 8** (`@vitejs/plugin-vue`).
- **Tailwind CSS 4** via `@tailwindcss/vite` — no separate `tailwind.config.js`; configuration is
  CSS-first (see `frontend/src/assets/main.css` / `base.css` if adding Tailwind directives/theme).
- Plain JavaScript, not TypeScript — `frontend/jsconfig.json` declares the `@/*` → `./src/*` path
  alias for editor tooling, but `frontend/vite.config.js` does not currently register a matching
  `resolve.alias`, so `@/` imports will not actually resolve at dev/build time until that's added.
- Entry point: `frontend/index.html` → `src/main.js` → mounts `src/App.vue` to `#app`.
