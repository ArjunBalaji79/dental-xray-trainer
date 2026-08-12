# ORBIT → CDM Platform Porting Tracker

Living document for migrating the ORBIT dashboard (this repo, `orbit_dashboard/`)
into Columbia's `pdm-app` platform (GitLab, branch `feature/new-ui-foundation`).
Last updated: **2026-08-05**.

---

## 1. Context

| | Source (this repo) | Target (`pdm-app`) |
|---|---|---|
| App | `orbit_dashboard/` — Flask + Jinja2, server-rendered | `src/frontend/` — Vue 3 SPA (Composition API, `<script setup>`), plain JS (no TS) |
| Build | none (Flask serves everything) | Vite 7, `npm run build:<env>` (`ide-linux`/`dev`/`tst`/`prod`) |
| Styling | `static/css/orbit.css` — 406 lines, all Epic tokens in one `:root` block, system font stack (no CDN fonts) | Bootstrap 5.3 + per-env SCSS (`src/frontend/src/assets/{ide-linux,dev,tst,prod}.scss`), `<style scoped>` in components |
| Routing | Flask routes | Vue Router 4 (`src/frontend/src/router.js`), path-based `publicRoutes` allowlist |
| Auth | none | Keycloak (`check-sso`), group gate `CDM_OrbitAppUsers` enforced in `router.beforeEach` and per-nav-item in `OrbitNavbar.vue` |
| Data | JSON built from Excel (`build_data.py` → `data/orbit.json`, plus `module{1,3,4,5}_cases.json`) | Phase 1–4: bundle JSON via Vite import. Phase 5: Flask API endpoints in `src/app/app.py` |
| Backend | Flask `app.py` (10 page routes, `/api/data`, `/api/module4/tutor`) | Same-repo Flask behind Nginx (`/api/*`), gunicorn, `@token_required` (Keycloak JWT) |
| Deploy | local only | GitLab CI → Docker (Alpine, builds frontend inside image) → Kubernetes (Kustomize, Traefik) at `orbit-dev.cdm.cumc.columbia.edu` |

Local reference copy of their repo (from zip, snapshot of `development` branch):
`scratchpad/pdm-app/pdm-app-orbit-development/` (session scratchpad — re-unzip from
`pdm-app-orbit-development (1).zip` on Desktop if gone).

## 2. Verified facts about the target (read from their code, not just their report)

- `vite.config.js` maps mode → env SCSS via the `@envstyle` alias; `main.js` imports it.
  Adding tokens to the four `assets/*.scss` files covers every environment.
- **Bootstrap is loaded twice**: `main.js` imports `bootstrap/dist/css/bootstrap.css`
  (stock, compiled) *and* `@envstyle` (which re-imports all of Bootstrap SCSS with
  `$primary` overridden). Pre-existing quirk (~200KB duplicate CSS). Do NOT fix in
  Phase 1; candidate cleanup PR later (remove the stock import).
- Their only custom properties are `--orbit-env-color` / `--orbit-env-color-soft`
  (set per env, consumed in `OrbitNavbar.vue` via `var(--env-color)` indirection).
  Bootstrap's own vars are `--bs-*`-prefixed → **no collisions** with our Epic token
  names (`--epic-navy`, `--action`, `--canvas`, `--ink`, …). Keeping our original
  token names so component CSS ports copy-paste clean from `orbit.css`.
- `$primary` (green `#228b22` in dev, differs per env) is the **environment
  discriminator**. Decision: never map Epic navy onto it; Epic tokens live alongside.
- `App.vue` shell: `OrbitNavbar` → `<main class="container-fluid"><div class="container">
  <router-view/></div></main>` → `OrbitFooter`. The inner `.container` constrains
  width — the Epic workspace (sidebar + canvas) wants full-bleed. Phase 2 must either
  route-scope the container or let ORBIT pages break out. Footer is `position:fixed`.
- `router.js`: routes import components eagerly; `publicRoutes` is an array of
  **paths** (not names); group gate applies to everything else.
- Navbar items are conditionally rendered with
  `keycloak && keycloak.authenticated && isAuthorized()` — follow this for ORBIT entries.
- `package.json` deps available for reuse: bootstrap-vue-next 0.43, primevue 4.5 +
  primeicons, axios, zod, konva 9.3, vuedraggable, vue-multiselect, sass-embedded.
  No ESLint/Prettier/tests/commitlint anywhere — match existing style by hand
  (2-space indent, single quotes, `<script setup>`).
- CI on feature branches: build-push → scan → test (SAST) → change-request →
  deploy (manual/auto) → clean. **No preview deploys for feature branches**; scan job
  currently red for infra reasons (pre-existing — `build-push` passing is the signal).
- Branch→env in Docker build: `main`→prod, `test`→tst, anything else→dev.
- CSP via Flask-Talisman is active, but our font stack is system fonts only → no CSP
  change needed for the UI port.

## 3. Decisions made

0. **Terminology: never say "Epic" in anything that lands in their repo** (code
   comments, commit messages, MR text, prompts). Epic = the EHR vendor; in a CUMC
   repo that's misleading. Say "ORBIT design system / ORBIT UI / ORBIT tokens".
   (Internally, this doc may still note that the visual style is Epic-inspired.)

1. **Epic tokens are additive** — separate `:root` block in each env SCSS; `$primary`,
   `--orbit-env-color*` untouched so the green/blue env cue keeps working.
2. **Two stacked headers for now** — keep their green navbar (env cue + login/identity);
   Epic command bar + dark sidebar render below it as the ORBIT pages' own layout.
   Consolidation is a later, deliberate step.
3. **ORBIT pages go behind the Keycloak `CDM_OrbitAppUsers` gate from day one**
   (i.e. NOT added to `publicRoutes`). Revisit only if a no-login demo is needed.
4. **Token names stay identical to `orbit.css`** for copy-paste fidelity (no
   collision risk; see §2).
5. **No new npm packages, no TypeScript** for the entire UI port (Phases 1–4).
6. Data ships as bundled JSON imports until Phase 5 wires real endpoints.

## 4. Source inventory (what must be ported)

Pages (Flask route → future Vue route):
- `/` overview · `/module/<n>` module detail · `/cases` case library ·
  `/case/<id>` case detail · `/interaction` interaction matrix · `/reference` reference
- Practice trainers: `/module/1/practice`, `/module/3/practice`, `/module/4/practice`,
  `/module/5/practice` (vanilla JS: `static/js/module{1,3,4,5}.js`, ~60KB total —
  becomes Vue reactive components)

Assets/data:
- `static/css/orbit.css` — tokens (Phase 1) + component classes (Phases 2–4, become scoped styles)
- `data/orbit.json` + `module{1,3,4,5}_cases.json` — bundle as imports (Phase 3–4)
- `static/img/case_*.jpg` (4 files, ~450KB) — Vite assets for now; later candidates for
  their authenticated image-API pattern (`/api/fmx/images`)
- Templates `templates/*.html` — structural reference for Vue components (Jinja
  `{% block %}` shell → `App.vue`/layout component + `<router-view/>`)

Backend (Phase 5, separate branch):
- `/api/data` equivalent; `/api/module4/tutor` → new route in their `src/app/app.py`
  with `@token_required`; Anthropic key via mounted Docker/K8s secrets (never in repo).

## 5. Phase plan & status

- [x] **Phase 1 — Design tokens**: Epic `:root` token block added to all four env
  SCSS files (2026-08-05). `npm run build:dev` passed (only pre-existing Sass
  deprecation + chunk-size warnings). Pushed as `5f8d4b25`; pipeline #550866:
  build-push ✅, scan ❌ (pre-existing infra failure, matches their other pipelines).
  **Phase 1 complete.**
- [x] **Phase 2 — Shell + navbar entry + Overview** (2026-08-05, built by their
  Sonnet 4.6 from `PHASE2_PROMPT.md`): `orbit/OrbitShell.vue` + `orbit/OrbitOverview.vue`
  created; `/orbit` route (auth-gated, `meta.orbitShell`), ORBIT navbar item,
  App.vue full-bleed branch. build:dev ✅ (362 modules). Visual check ✅.
  `ab6136` added to `CDM_OrbitAppUsers`; authenticated flow verified locally.
  publicRoutes hack reverted, pushed, build-push ✅. **Phase 2 complete.**
- [x] **Phase 3 — Static pages** (2026-08-05; visual check ✅, pushed, MR merged
  to `development` by Arjun — sole maintainer, direct-merge OK'd — deploy-auto ✅,
  **verified live on orbit-dev.cdm.cumc.columbia.edu** with ORBIT navbar item +
  all pages working authenticated):
  Module Detail, Case Library (client-side filters), Case Detail (steps from
  buildout), Interaction Matrix, Reference. Data bundled: Arjun must copy
  `orbit_dashboard/data/orbit.json` → their
  `src/frontend/src/components/orbit/orbit-data.json` BEFORE running the prompt.
  Adds orbitData.js + DiffPill/OrbitChip components; OrbitShell gets a
  storyboard slot + live tab links; `.binary .btn` renamed `.bin-btn`
  (Bootstrap collision).
- [ ] **Phase 4 — Interactive trainers** *(split per module; 4a prompt ready in
  `PHASE4A_PROMPT.md`)*: order 4a=M1 → 4b=M3 → 4c=M5 → 4d=M4 (flagship, tutor).
  Images: all of `static/img/` (denpar/ + 4 case jpgs, ~1.8MB) copied once in 4a
  to their `src/frontend/public/orbit-img/`. Case JSONs copied per phase into
  `components/orbit/moduleN-cases.json`. Full trainer CSS lands once in 4a
  (OrbitShell). `PRACTICE_ROUTES` map in orbitData.js drives the module page's
  Launch-practice button per ported module. M4 tutor: client-side scripted coach
  in Phase 4d (port of `_scripted_tutor` + the JS catch fallback); real
  `/api/module4/tutor` endpoint arrives in Phase 5.
- [ ] **Phase 5 — Backend + data (new branch off `development` after UI merges)**:
  Flask endpoints, AI-tutor proxy, secrets wiring (Kustomize + docker-compose),
  swap JSON imports → axios with Keycloak bearer token.

## 6. Risks / open questions

- Env-color decision (§3.1) worth a quick confirm with their team before the PR.
- No feature-branch preview deploys → verification is local `npm run dev` /
  `build:dev` only until merge to `development`.
- ~~Their `development` branch moves (Fedor active) — rebase before MR.~~
  Update 2026-08-05: Arjun is the sole active maintainer of this app and has
  explicit permission to merge MRs to `development` directly. Workflow per
  phase: feature branch → MR (for the record) → self-merge → deploy-auto →
  verify on orbit-dev. Still rebase before each MR as hygiene.
- Double-Bootstrap import (§2) — flag to team; don't bundle the fix into UI PRs.
- K8s readinessProbe commented out — matters when the AI-tutor endpoint lands (Phase 5).
- Zip snapshot ≠ live repo: re-verify `router.js` / `OrbitNavbar.vue` / env SCSS
  haven't drifted before each prompt is run.

## 7. Log

- **2026-08-05** — Discovery prompt run in their repo (read-only); porting guide
  received. Verified against zip of their `development` branch: guide accurate; found
  the double-Bootstrap import it missed. Decisions §3 taken. Phase 1 prompt drafted.
- **2026-08-05** — Phase 1 executed by their Claude: tokens in all four env SCSS
  files, build:dev green, nothing else touched. Note: npm commands must run from
  `src/frontend/`, not repo root. Next: review diff → commit → push → Phase 2.
- **2026-08-05** — Phase 1 pushed (`5f8d4b25`) and pipeline-verified. Verified
  locally too: https://localhost:5173 (server is HTTPS-only; purple navbar =
  ide-linux env color, expected). Phase 2 prompt written to `PHASE2_PROMPT.md`:
  OrbitShell.vue + OrbitOverview.vue, `/orbit` route (auth-gated, `meta.orbitShell`),
  navbar item, App.vue full-bleed branch, structural CSS ported from orbit.css
  with `.workspace`-prefixed collision guards (progress/card/footer/link collide
  with Bootstrap class names).
