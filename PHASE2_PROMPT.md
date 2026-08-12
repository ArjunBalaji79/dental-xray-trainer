# Phase 2 prompt — paste everything below the line into their Claude

---

We're on the `feature/new-ui-foundation` branch. Phase 1 (ORBIT design tokens in
the four env SCSS files) is merged into this branch and building. Now execute
Phase 2 of the ORBIT UI migration: add an ORBIT entry to the navbar, one
auth-gated route, and a static ORBIT Overview page with its own workspace layout.

Everything is additive. All existing routes, demos, and components must keep
working unchanged.

## Files to create (2) and edit (3) — nothing else

Create:
  src/frontend/src/components/orbit/OrbitShell.vue      (layout: command bar + sidebar + content slot)
  src/frontend/src/components/orbit/OrbitOverview.vue   (the Overview page, uses OrbitShell)

Edit:
  src/frontend/src/router.js          (one new route)
  src/frontend/src/components/OrbitNavbar.vue   (one new nav item)
  src/frontend/App.vue                (full-bleed support via route meta — see below)

## Router change

Add to `routes` (do NOT add to `publicRoutes` — this page requires Keycloak
login + the CDM_OrbitAppUsers group, which the existing `beforeEach` guard
already enforces for any route not in `publicRoutes`):

```js
{ path: '/orbit', name: 'orbit', component: OrbitOverviewPage, meta: { orbitShell: true } },
```

with the matching eager import at the top, following the existing import style.

## Navbar change

In OrbitNavbar.vue, add a top-level nav item labeled `ORBIT` immediately after
the About item, gated exactly like the Info/About items
(`v-if="keycloak && keycloak.authenticated && isAuthorized()"`), routing to
`{ name: 'orbit' }` with the same `:active` pattern.

## App.vue change (full-bleed)

The current shell wraps every page in `<main class="container-fluid ...">
<div class="container">`. The ORBIT workspace needs full width. Use the route
meta flag: when `route.meta.orbitShell` is true, render `<router-view/>`
directly (no `main`/`container` wrappers and no bottom padding); otherwise keep
the existing markup exactly as is. Use `useRoute()` in App.vue's script setup.
Keep `<OrbitNavbar/>` and `<OrbitFooter/>` rendering in both branches — the
green navbar stays on top of ORBIT pages (it carries the environment color and
login controls).

## OrbitShell.vue

A layout component: props `activeTab` (string); renders the ORBIT command bar,
a left sidebar, and a `<slot/>` in the content canvas. Structure (translate to
a Vue template; router-links where noted):

```html
<header class="app-bar">
  <router-link class="brand" :to="{name:'orbit'}">
    <span class="brand-mark">ORBIT</span>
    <span class="brand-sub">Oral Radiology Board-Interpretation Trainer</span>
  </router-link>
  <nav class="tabstrip" aria-label="Workspace activities">
    <!-- One .tab per entry; only Overview routes anywhere today.
         The other four are inert placeholders (render as <span class="tab">,
         they get routes in Phase 3): -->
    <!-- Overview (router-link, class "tab tab--active" when activeTab==='overview') -->
    <!-- Modules · Case Library · Interaction Matrix · Reference (spans) -->
  </nav>
  <div class="bar-right">
    <div class="identity" :title="username">
      <div class="avatar">{{ userInitials }}</div>
      <span class="name">{{ username }}</span>
    </div>
  </div>
</header>

<div class="workspace">
  <aside class="storyboard" aria-label="Storyboard">
    <div class="sb-eyebrow">Program</div>
    <div class="sb-title">ORBIT Curriculum</div>
    <div class="sb-goal">AI-assisted dental radiology education — curriculum console</div>
    <div class="sb-div"></div>
    <!-- five .sb-row entries; each is:
         <div class="sb-row"><div><div class="sb-fl">LABEL</div><div class="sb-fv">VALUE</div></div></div>
         Labels/values: Modules→8 · Objectives→62 measurable · Authored cases→18
                        · Activity steps→45 · AI-comparison→5 modules -->
    <div class="sb-div"></div>
    <div class="sb-fl" style="margin-bottom:8px">Jump to module</div>
    <!-- eight .sb-plain-item entries (plain <span> wrappers for now, links in Phase 3):
         M1 Image Quality and Error Correction · M2 Radiographic Mounting ·
         M3 Tooth Identification and Localization · M4 Normal Anatomy vs Pathology ·
         M5 Radiographic Interpretation & AI Comparison · M6 Clinical Documentation
         and EHR Simulation · M7 Panoramic View · M8 Advanced Cases & Clinical
         Decision Making
         Each: <div class="sb-li-id">M{n}</div><div class="sb-li-name">{title}</div> -->
  </aside>
  <main class="canvas">
    <slot />
    <div class="footer">
      ORBIT · Oral Radiology Board-Interpretation Trainer · Dr. Perelman AIxEducation Project — Curriculum Console<br>
      <span style="color:var(--muted)">Radiographs: DenPAR (Rasnayaka et al., 2025), CC BY 4.0 · panoramics: DENTEX (MICCAI 2023)</span>
    </div>
  </main>
</div>
```

For `username` / `userInitials`: use the `useKeycloak` composable the way
OrbitNavbar.vue does (`keycloak.tokenParsed.preferred_username`), with initials
derived from it; fall back to 'Curriculum Author' / 'CA' when unavailable.

Put the ORBIT structural CSS (below) in OrbitShell.vue as a NON-scoped
`<style>` block (it must style the page content passed through the slot and
the Overview page's classes; all selectors are ORBIT-specific class names so
they can't leak into Bootstrap pages, which never render these classes).
Override note: the shell's `.footer` class collides with nothing in Bootstrap,
but their global `footer { position:fixed; bottom:0 }` element rule exists —
our footer is a `div.footer`, not a `<footer>` element, so it's unaffected.

## OrbitOverview.vue

Wraps everything in `<OrbitShell active-tab="overview">`. Static content, all
data hardcoded (real numbers from the source app). Structure:

```html
<div class="section-banner">
  <span class="section-kicker">Overview</span>
  <h2>Program Dashboard</h2>
  <span class="sub">Curriculum authoring &amp; coverage · Dr. Perelman AIxEducation Project</span>
</div>

<div class="kpi-row">
  <!-- six .kpi-tile blocks, each:
       <div class="kpi-num tabular">N</div><div class="kpi-cap">CAP</div><div class="kpi-note">NOTE</div>
       8 / Modules / Image Quality → Advanced Cases
       62 / Objectives / 62 carry a measurable target
       18 / Authored Cases / Expert-labeled radiographs
       45 / Activity Steps / Interactive CaseBuildout steps
       3 / Difficulty Tiers / Obvious · Moderate · Subtle
       5 / AI-Comparison / Modules 4, 5, 6, 7, 8 -->
</div>

<div class="card" style="margin-bottom:12px">
  <div class="card-head"><span class="keyline"></span><h3>Module Coverage</h3>
    <div class="actions"><span class="pts">bar = cases authored vs. M1 (10)</span></div>
  </div>
  <div class="card-body">
    <div class="grid-cards">
      <!-- eight .mod-mini blocks (render with v-for over a hardcoded array).
           Each: <div class="mnum">Module {n}</div>
                 <div class="mtitle">{title} <span v-if="ai" class="chip chip--ai">AI</span></div>
                 <div class="mstats"><span><b>{obj}</b> obj</span><span><b>{cases}</b> cases</span></div>
                 <div class="progress"><span :style="{width: (100*cases/10)+'%'}"></span></div>
           Data (n, title, obj, cases, ai):
           1, Image Quality and Error Correction, 6, 10, false
           2, Radiographic Mounting, 6, 0, false
           3, Tooth Identification and Localization, 6, 0, false
           4, Normal Anatomy vs Pathology, 7, 4, true
           5, Radiographic Interpretation & AI Comparison, 9, 4, true
           6, Clinical Documentation and EHR Simulation, 9, 0, true
           7, Panoramic View, 9, 0, true
           8, Advanced Cases & Clinical Decision Making, 10, 0, true -->
    </div>
  </div>
</div>

<div class="grid-2" style="margin-bottom:12px">
  <div class="card">
    <div class="card-head"><span class="keyline"></span><h3>Cases · Continue Authoring</h3>
      <div class="actions"><span class="pts">18 total</span></div>
    </div>
    <div class="grid-wrap">
      <table class="data-grid">
        <thead><tr><th>Case ID</th><th>Case Name</th><th class="num">Module</th><th>Difficulty</th><th class="num">Steps</th><th>Status</th></tr></thead>
        <tbody>
          <!-- v-for over hardcoded rows (id, name, module, difficulty 1-3, steps, status):
               M1-01, Cone Cut BW, 1, 1, 0, Author
               M1-02, Horizontal Overlap BW, 1, 2, 5, Open
               M1-03, Elongated PA, 1, 2, 5, Open
               M1-04, Foreshortened Premolar PA, 1, 2, 5, Open
               M1-05, Motion Blur Molar BW, 1, 1, 5, Open
               M1-06, Light Exposure BW, 1, 1, 5, Open
               Cells: <td><span class="cid">{id}</span></td><td class="cname">{name}</td>
                      <td class="num tabular">{module}</td><td>[difficulty pill]</td>
                      <td class="num tabular">{steps}</td>
                      <td><span class="link">Open</span> or <span class="pts">Author</span></td>
               Difficulty pill markup:
               <span :class="'pill pill--diff'+d">Diff {d}
                 <span class="dots"><i v-for="i in 3" :class="['dot', {off: i>d}]"></i></span>
               </span> -->
        </tbody>
      </table>
    </div>
  </div>

  <div style="display:flex; flex-direction:column; gap:12px">
    <div class="card">
      <div class="card-head"><span class="keyline"></span><h3>Difficulty Mix</h3></div>
      <div class="card-body">
        <!-- three .mix-row entries (max count = 11):
             <div class="mix-row">
               <div class="mix-lab">[pill, label=level number only] {label}</div>
               <div class="mix-track"><div class="mix-fill" :style="width %, background, color">{count}</div></div>
               <div class="mix-count tabular">{count}</div>
             </div>
             Rows: level 1 "Obvious / basic" 5 (fill var(--diff1-fill), text var(--diff1-text))
                   level 2 "Moderate" 11 (var(--diff2-fill) / var(--diff2-text))
                   level 3 "Subtle / complex" 2 (var(--diff3-fill) / #fff) -->
      </div>
    </div>
    <div class="card">
      <div class="card-head"><span class="keyline"></span><h3>Objective Targets</h3></div>
      <div class="card-body" style="display:flex; align-items:center; gap:14px">
        <div><div class="kpi-num tabular">62</div><div class="kpi-cap">carry a target</div></div>
        <div class="callout" style="flex:1"><div class="ct">Every objective sets a measurable <b>mastery threshold</b> — most require <b>≥90%</b> accuracy; AI-gain objectives target <b>≥15%</b> improvement.</div></div>
      </div>
    </div>
  </div>
</div>

<div class="callout">
  <div class="ct"><b>AI-comparison is planned</b> for Modules 4–8 — students reason through the case first, then compare against an AI tutor and refine their answer through dialogue.</div>
</div>
```

## The ORBIT structural CSS (goes in OrbitShell.vue's non-scoped style block)

Copy verbatim — these selectors consume the Phase 1 tokens:

```css
.tabular{font-variant-numeric:tabular-nums}
.app-bar{position:sticky; top:0; z-index:50; height:44px; display:flex; align-items:stretch;
  background:var(--epic-navy); border-bottom:1px solid var(--navy-deep);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.08); font-family:var(--font); font-size:var(--fs-body);}
.app-bar .brand{display:flex; align-items:center; gap:8px; padding:0 14px 0 16px; flex:0 0 auto; text-decoration:none}
.brand-mark{font-size:15px; font-weight:600; color:#fff; letter-spacing:.02em}
.brand-sub{font-size:12px; color:rgba(255,255,255,.7); white-space:nowrap}
@media(max-width:900px){.brand-sub{display:none}}
.tabstrip{display:flex; align-items:stretch; margin-left:6px; overflow-x:auto; scrollbar-width:none}
.tabstrip::-webkit-scrollbar{display:none}
.tabstrip .tab{display:flex; align-items:center; padding:0 12px; height:44px; font-size:13px;
  color:rgba(255,255,255,.78); white-space:nowrap; cursor:pointer; border:0; background:transparent;
  text-decoration:none; border-top:2px solid transparent;}
.tabstrip .tab:hover{background:rgba(255,255,255,.10); color:#fff}
.tabstrip .tab--active{background:var(--canvas); color:var(--ink); font-weight:600;
  border-radius:4px 4px 0 0; border-top:2px solid var(--action);}
.tabstrip .tab--active:hover{background:var(--canvas); color:var(--ink)}
.bar-right{margin-left:auto; display:flex; align-items:center; gap:12px; padding:0 14px}
.identity{display:flex; align-items:center; gap:8px; cursor:pointer}
.identity .avatar{width:24px; height:24px; border-radius:50%; background:rgba(255,255,255,.15);
  display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:600; color:#fff}
.identity .name{font-size:12px; color:#fff; white-space:nowrap}
@media(max-width:720px){.identity .name{display:none}}

.workspace{display:flex; align-items:stretch; min-height:calc(100vh - 44px);
  font-family:var(--font); font-size:var(--fs-body); color:var(--ink); line-height:1.4; background:var(--canvas)}
.workspace a{color:var(--action)}
.storyboard{flex:0 0 260px; width:260px; background:var(--slate); border-right:1px solid var(--navy-deep);
  padding:14px; position:sticky; top:44px; align-self:flex-start; height:calc(100vh - 44px); overflow-y:auto;}
@media(max-width:820px){.storyboard{display:none}}
.workspace .canvas{flex:1 1 auto; min-width:0; padding:16px; background:var(--canvas)}

.sb-eyebrow{font-size:12px; font-weight:600; text-transform:uppercase; letter-spacing:.04em; color:var(--rail-label)}
.sb-title{font-size:15px; font-weight:600; color:#fff; margin:4px 0 2px}
.sb-goal{font-size:12px; color:rgba(255,255,255,.72); line-height:1.45}
.sb-div{height:1px; background:rgba(255,255,255,.08); margin:14px 0}
.sb-row{display:flex; align-items:flex-start; gap:6px; margin-bottom:14px}
.sb-fl{font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:.03em; color:var(--rail-sub)}
.sb-fv{font-size:13px; color:var(--rail-value); margin-top:2px}
.sb-plain-item{display:block; text-decoration:none; padding:8px 10px 8px 13px; margin:0 -14px 4px; border-left:3px solid transparent}
.sb-plain-item:hover{background:rgba(255,255,255,.04); border-left-color:rgba(255,255,255,.15)}
.sb-li-id{font-size:12px; font-weight:600; color:var(--rail-value); font-variant-numeric:tabular-nums}
.sb-li-name{font-size:12px; color:rgba(255,255,255,.72)}

.section-banner{display:flex; align-items:center; gap:10px; margin:0 0 12px; padding:8px 0; border-bottom:1px solid var(--border);}
.section-kicker{font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.06em; color:#fff;
  background:var(--action); padding:3px 8px; border-radius:3px}
.section-banner h2{font-size:15px; font-weight:600; margin:0; color:var(--ink)}
.section-banner .sub{font-size:12px; color:var(--muted); margin-left:auto; text-align:right}

.kpi-row{display:grid; grid-template-columns:repeat(6,1fr); gap:12px; margin-bottom:12px}
@media(max-width:1200px){.kpi-row{grid-template-columns:repeat(3,1fr)}}
@media(max-width:560px){.kpi-row{grid-template-columns:repeat(2,1fr)}}
.kpi-tile{background:var(--card); border:1px solid var(--border); border-radius:var(--r-card);
  box-shadow:var(--shadow-card); padding:14px 16px; min-height:78px;}
.kpi-num{font-size:var(--fs-kpi); font-weight:700; color:var(--ink); font-variant-numeric:tabular-nums; line-height:1}
.kpi-cap{font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:.03em; color:var(--muted); margin-top:6px}
.kpi-note{font-size:11px; color:var(--muted); margin-top:4px; line-height:1.35}

.workspace .card{background:var(--card); border:1px solid var(--border); border-radius:var(--r-card); box-shadow:var(--shadow-card); overflow:hidden}
.card-head{min-height:32px; display:flex; align-items:center; gap:8px; padding:0 12px; background:#fff; border-bottom:1px solid var(--border);}
.card-head .keyline{width:3px; height:16px; background:var(--action); border-radius:2px; flex:0 0 3px}
.card-head h3{font-size:12px; font-weight:600; text-transform:uppercase; letter-spacing:.02em; color:var(--ink); margin:0}
.card-head .actions{margin-left:auto; display:flex; align-items:center; gap:12px}
.workspace .link{color:var(--action); font-size:12px; text-decoration:none; cursor:pointer; background:none; border:0; padding:0; font-family:inherit}
.workspace .link:hover{color:var(--action-hover); text-decoration:underline}
.workspace .card-body{padding:14px}

.grid-2{display:grid; grid-template-columns:2fr 1fr; gap:12px; align-items:start}
@media(max-width:1000px){.grid-2{grid-template-columns:1fr}}
.grid-cards{display:grid; grid-template-columns:repeat(4,1fr); gap:12px}
@media(max-width:1100px){.grid-cards{grid-template-columns:repeat(2,1fr)}}
@media(max-width:600px){.grid-cards{grid-template-columns:1fr}}

.mod-mini{display:block; text-decoration:none; background:var(--card); border:1px solid var(--border);
  border-radius:var(--r-card); box-shadow:var(--shadow-card); padding:12px; transition:border-color .12s, box-shadow .12s}
.mod-mini:hover{border-color:var(--action); box-shadow:0 2px 6px rgba(16,24,40,.10)}
.mod-mini .mnum{font-size:11px; font-weight:700; color:var(--muted); text-transform:uppercase; letter-spacing:.04em}
.mod-mini .mtitle{font-size:13px; font-weight:600; color:var(--ink); margin:4px 0 6px; line-height:1.3}
.mod-mini .mstats{display:flex; gap:14px; font-size:12px; color:var(--muted); align-items:center}
.mod-mini .mstats b{color:var(--ink); font-weight:600; font-variant-numeric:tabular-nums}
.workspace .progress{height:6px; background:var(--header-gray); border-radius:3px; margin-top:10px; overflow:hidden}
.workspace .progress>span{display:block; height:100%; background:var(--action)}

.mix-row{display:flex; align-items:center; gap:10px; margin-bottom:12px}
.mix-row:last-child{margin-bottom:0}
.mix-lab{flex:0 0 132px; font-size:12px; color:var(--muted); display:flex; align-items:center; gap:6px}
.mix-track{flex:1 1 auto; height:20px; background:var(--header-gray); border-radius:3px; overflow:hidden}
.mix-fill{height:100%; display:flex; align-items:center; padding-left:8px; font-size:11px; font-weight:700; color:#fff; min-width:2px}
.mix-count{flex:0 0 34px; text-align:right; font-size:12px; font-weight:600; color:var(--ink); font-variant-numeric:tabular-nums}

.callout{display:flex; gap:10px; align-items:flex-start; padding:12px; background:var(--ai-fill);
  border:1px solid var(--ai-border); border-radius:var(--r-card)}
.callout .ct{font-size:12px; color:var(--ink); line-height:1.45}
.callout .ct b{color:var(--ai-text)}

.grid-wrap{overflow-x:auto}
table.data-grid{border-collapse:collapse; width:100%; min-width:720px}
.data-grid thead th{background:var(--header-gray); text-align:left; font-size:11px; font-weight:600;
  text-transform:uppercase; letter-spacing:.03em; color:var(--muted); padding:7px 10px;
  border-bottom:2px solid var(--border); white-space:nowrap;}
.data-grid th.num,.data-grid td.num{text-align:right; font-variant-numeric:tabular-nums}
.data-grid tbody td{padding:6px 10px; font-size:13px; color:var(--ink); border-bottom:1px solid var(--cell-sep); vertical-align:middle}
.data-grid tbody tr{height:31px}
.data-grid tbody tr:nth-child(even){background:var(--zebra)}
.data-grid tbody tr:hover{background:var(--row-hover)}
.cid{font-size:12px; font-weight:600; color:var(--ink-strong); font-variant-numeric:tabular-nums; white-space:nowrap; text-decoration:none}
.cname{font-weight:600; color:var(--ink)}
.pts{font-size:11px; color:var(--muted); font-weight:600}

.pill{display:inline-flex; align-items:center; gap:5px; height:20px; padding:0 8px; border-radius:var(--r-pill); font-size:11px; font-weight:600; white-space:nowrap}
.pill--diff1{background:var(--diff1-fill); color:var(--diff1-text)}
.pill--diff2{background:var(--diff2-fill); color:var(--diff2-text)}
.pill--diff3{background:var(--diff3-fill); color:var(--diff3-text)}
.dots{display:inline-flex; gap:2px}
.dot{width:5px; height:5px; border-radius:1px; background:currentColor; opacity:.9}
.dot.off{opacity:.25}
.chip{display:inline-flex; align-items:center; height:20px; padding:0 8px; border-radius:var(--r-chip); font-size:11px; font-weight:600; background:var(--neutral-fill); color:var(--neutral-text); white-space:nowrap}
.chip--ai{background:var(--ai-fill); border:1px solid var(--ai-border); color:var(--ai-text)}

.workspace .footer{padding:20px 0 8px; text-align:center; font-size:11px; color:var(--muted); position:static}
```

## Hard constraints

- Plain JavaScript, `<script setup>`, 2-space indent, single quotes — match the
  existing components. No TypeScript.
- No new npm packages, no lockfile changes. No icon libraries — if you add any
  decorative icons, use small inline SVGs; skipping icons entirely is fine.
- Do not touch: the four env SCSS files, main.js, vite.config.js, package.json,
  anything under src/app/, any existing demo/page component.
- Do not put the word "Epic" anywhere — call everything ORBIT (ORBIT design
  system, ORBIT shell, ORBIT tokens).
- All existing routes and demos must still work; run `npm run build:dev` from
  src/frontend and confirm it passes.
- Then list every file you created/changed with a one-line summary each, and
  stop. Do not commit or push — I'll review, test locally, and commit myself.
