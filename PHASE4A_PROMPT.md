# Phase 4a prompt — Module 1 interactive trainer

## BEFORE running this prompt (manual steps for Arjun)

1. Copy `orbit_dashboard/data/module1_cases.json` from the Mac into their repo:

       src/frontend/src/components/orbit/module1-cases.json

2. Copy the radiograph images (one-time; serves phases 4a–4d). From the Mac's
   `orbit_dashboard/static/img/`, copy BOTH the `denpar/` folder (20 jpgs) and
   the four `case_*.jpg` files into their repo at:

       src/frontend/public/orbit-img/denpar/...   (20 files)
       src/frontend/public/orbit-img/case_cervical_burnout.jpg
       src/frontend/public/orbit-img/case_maxillary_sinus.jpg
       src/frontend/public/orbit-img/case_mental_foramen.jpg
       src/frontend/public/orbit-img/case_nutrient_canal.jpg

   (~1.8MB total. Files in `public/` are served at the site root, so
   `/orbit-img/denpar/m1_M1-02.jpg` will resolve.)

---
Paste everything below this line into their Claude.
---

We're on the `feature/new-ui-foundation` branch. Phases 1–3 of the ORBIT UI
migration are merged and live. Now execute Phase 4a: port the Module 1
interactive trainer (Image Quality & Error Correction) — the first of four
practice modules. A learner works 10 radiograph cases through a 5-step flow
(diagnostic quality → identify error → cause → correction → visual comparison),
scored with per-step feedback and an objective-mapped results screen.

FIRST verify these exist (I placed them manually) — if either is missing, STOP:
- src/frontend/src/components/orbit/module1-cases.json
- src/frontend/public/orbit-img/denpar/  (contains m1_*.jpg files)

## Files

Create:
- src/frontend/src/components/orbit/OrbitModule1Practice.vue

Edit:
- src/frontend/src/router.js — add route
  `{ path: '/orbit/module/1/practice', name: 'orbit-module1-practice', component: ..., meta: { orbitShell: true } }`
  (eager import; NOT in publicRoutes).
- src/frontend/src/components/orbit/orbitData.js — export
  `const PRACTICE_ROUTES = { 1: 'orbit-module1-practice' }` (modules 3, 4, 5
  get added in later phases).
- src/frontend/src/components/orbit/OrbitModule.vue — where the module page
  currently shows the "Practice · coming in Phase 4" chip: if
  PRACTICE_ROUTES[module.number] exists, render instead a
  `<router-link class="btn-primary" :to="{name: PRACTICE_ROUTES[n]}">Launch practice</router-link>`
  in BOTH places the source template had it (the sidebar full-width button and
  the mod-header right side). Modules without an entry keep the current chip.
- src/frontend/src/components/orbit/OrbitShell.vue — append the "Trainer CSS"
  block (bottom of this prompt) to the existing non-scoped style block. This is
  the complete CSS for all four trainers, added once — later phases won't touch
  it again.

## The source implementation (this is the spec — reproduce its behavior exactly)

Below is the original vanilla-JS trainer verbatim. Port it to a Vue component
with reactive state. It renders three views: intro, step, summary.

Translation guidance:
- State: `view` ('intro'|'step'|'summary'), `idx` (case index), `sub` (step
  index), `records` (per-case array of per-step results, null = unanswered).
  All the DOM-rebuilding render functions become template sections with
  v-if/v-for; the manual innerHTML/esc()/wireStep machinery disappears —
  Vue handles escaping and events.
- Data: `import m1 from './module1-cases.json'` — shape:
  `{ module: {title, goal, objectives[]}, cases[], total_points }`. Each case:
  `{ id, name, modality, finding, pearl, image, steps[] }`; each step:
  `{ n, key, objective, prompt, answer_type, options[], expected, feedback, points }`.
- IMGBASE becomes '/orbit-img/' — case images render as
  `<img :src="'/orbit-img/' + c.image">` when `c.image` is set, else the
  `.p1-film` placeholder div (corners + modality label) as in filmHTML().
- The answer-matching rule must be ported exactly (it's how correct options
  are recognized): normalize both sides to lowercase/trimmed with spaces
  around them, then `expected.includes(option)` — see norm()/isCorrect().
- The visual-comparison step (`answer_type` contains 'visual') auto-completes:
  mark its record `{reviewed: true, ok: true}` when first shown and show the
  Continue button immediately.
- Two-option steps get the `choices--two` grid class, as in the source.
- The storyboard (OrbitShell's #storyboard slot) replaces the old sidebar DOM
  pokes (sb-score / sb-acc / sb-caselist): show module title + goal, "Error
  cases" count, live "Session score" (earned + ' / ' + total_points + ' pts'),
  live "Diagnostic calls" (ok/done of the diagnostic steps, '—' when none
  answered), and the case list where the ACTIVE case uses class `sb-list-item`
  and the rest `sb-plain-item` (computed from `idx`) — clicking them does
  nothing (same as source).
- The progress bar (p4-progresswrap) shows only in the step view: percent =
  completed steps / total steps across all cases; label "Case N of 10"; right
  label = earned points.
- Summary view: port renderSummary() faithfully — the four kpi tiles, the
  per-objective rows (objRes mapping by objective number with hit/miss icons),
  the callout, Restart (resets all state back to intro) and a "Back to
  Module 1" btn-ghost router-link to the module page.
- Breadcrumbs at top of all three views: Overview › Module 1 › Practice
  (router-links for the first two).
- The small check/X/arrow icons: keep as tiny inline SVGs (a local component
  or v-html constants are both fine).
- `window.scrollTo({top: 0, behavior: 'smooth'})` on view/step change stays.

```js
/* ORBIT — Module 1 interactive trainer (Image Quality & Error Correction).
   A learner works each case through the real 5-step CaseBuildout flow:
   diagnostic quality -> identify error -> cause -> correction -> visual comparison.
   Scored, with per-step feedback and an objective-mapped results screen.
   Reuses the Module-4 practice CSS classes; no AI tutor (Module 1 has no AI objective). */
(function () {
  "use strict";

  var DATA = JSON.parse(document.getElementById("m1-data").textContent);
  var CASES = DATA.cases;
  var OBJ = DATA.module.objectives;
  var TOTAL_PTS = DATA.total_points;

  var STEP_LABEL = { diagnostic: "Diagnostic quality", error: "Identify the error",
    cause: "Determine the cause", correction: "Select the correction", compare: "Review the correction" };

  var app = document.getElementById("p1-app");
  var progress = document.getElementById("p1-progress");

  var IMGBASE = "/static/img/";
  var state, records;
  function reset() {
    state = { idx: 0, sub: 0 };
    records = CASES.map(function (c) { return c.steps.map(function () { return null; }); });
  }

  function h() {}
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function icon(path, sw) { return '<svg class="glyph" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="' + (sw || 1.6) + '" stroke-linecap="round" stroke-linejoin="round">' + path + "</svg>"; }
  var I_CHECK = icon('<path d="M20 6 9 17l-5-5"/>', 2);
  var I_X = icon('<path d="M18 6 6 18M6 6l12 12"/>', 2);
  var I_ARROW = icon('<path d="M5 12h14M12 5l7 7-7 7"/>');

  function norm(s) { return " " + String(s || "").toLowerCase().trim() + " "; }
  function isCorrect(opt, expected) { var o = norm(opt), e = norm(expected); return o.trim() !== "" && (e.indexOf(o) !== -1); }

  function earned() {
    var p = 0;
    CASES.forEach(function (c, ci) {
      c.steps.forEach(function (s, si) {
        var r = records[ci][si];
        if (r && r.ok) p += s.points;
      });
    });
    return p;
  }

  function updateChrome() {
    var totalSteps = 0, done = 0;
    CASES.forEach(function (c, ci) {
      totalSteps += c.steps.length;
      if (ci < state.idx) done += c.steps.length;
      else if (ci === state.idx) done += state.sub;
    });
    var pct = Math.round((done / totalSteps) * 100);
    var bar = document.getElementById("p1-bar"); if (bar) bar.style.width = pct + "%";
    var lab = document.getElementById("p1-lab"); if (lab) lab.textContent = "Case " + (state.idx + 1) + " of " + CASES.length;
    var sc = document.getElementById("p1-score"); if (sc) sc.textContent = earned() + " pts";
    var sbs = document.getElementById("sb-score"); if (sbs) sbs.textContent = earned() + " / " + TOTAL_PTS + " pts";
    var diag = diagStats();
    var sba = document.getElementById("sb-acc"); if (sba) sba.textContent = diag.done ? (diag.ok + " / " + diag.done + " correct") : "—";
    document.querySelectorAll("#sb-caselist [data-caseidx]").forEach(function (n) {
      var i = +n.getAttribute("data-caseidx");
      n.className = i === state.idx ? "sb-list-item" : "sb-plain-item";
    });
  }

  function diagStats() {
    var ok = 0, done = 0;
    CASES.forEach(function (c, ci) {
      var si = c.steps.findIndex(function (s) { return s.key === "diagnostic"; });
      if (si >= 0 && records[ci][si]) { done++; if (records[ci][si].ok) ok++; }
    });
    return { ok: ok, done: done };
  }

  function filmHTML(c) {
    var inner = c.image
      ? '<div class="imgwrap"><img src="' + IMGBASE + esc(c.image) + '" alt="radiograph"></div>'
      : '<div class="p1-film"><div class="p1-corner tl"></div><div class="p1-corner tr"></div><div class="p1-corner bl"></div><div class="p1-corner br"></div><div class="p1-mod">' + esc(c.modality) + ' · ' + esc(c.id) + '</div></div>';
    var cap = c.image ? 'DenPAR intra-oral periapical · technique error simulated for training'
                      : 'Representative film · illustrative (reference image pending)';
    return '<div class="p4-view">' + inner +
      '<div class="vcap"><div class="roinote">' + cap + '</div>' +
      '<div class="finding">' + esc(c.finding) + '</div></div></div>';
  }

  function choicesHTML(options, expected, chosen, locked) {
    return '<div class="choices">' + options.map(function (opt) {
      var correct = isCorrect(opt, expected);
      var cls = "choice";
      if (locked) { if (correct) cls += " correct"; else if (opt === chosen) cls += " wrong"; else cls += " muted"; }
      else if (opt === chosen) cls += " selected";
      var mark = (locked && correct) ? I_CHECK : (locked && opt === chosen) ? I_X : "";
      var tag = locked ? (correct ? '<span class="tag">Correct</span>' : (opt === chosen ? '<span class="tag">Your pick</span>' : "")) : "";
      return '<button class="choice ' + cls.slice(7) + '" data-opt="' + esc(opt) + '"' + (locked ? " disabled" : "") + '>' +
        '<span class="mark">' + mark + '</span><span class="txt">' + esc(opt) + "</span>" + tag + "</button>";
    }).join("") + "</div>";
  }

  function feedbackHTML(ok, body) {
    return '<div class="feedback ' + (ok ? "ok" : "no") + '"><div class="lead">' + (ok ? I_CHECK : I_X) +
      (ok ? "Correct" : "Not quite") + "</div><div>" + esc(body) + "</div></div>";
  }

  // ---- INTRO ---------------------------------------------------------------
  function renderIntro() {
    progress.style.display = "none";
    app.innerHTML =
      '<div class="p4-hero"><h1>Module 1 — Image Quality &amp; Error Correction</h1>' +
      '<div class="lead">' + esc(DATA.module.goal) + "</div>" +
      '<div class="obj-grid">' + OBJ.map(function (o) {
        var badge = o.target ? '<span class="mastery">' + o.target + "</span>" : "";
        return '<div class="obj-card"><div class="n">' + o.n + '</div><div><div class="t">' + esc(o.text) + "</div>" + badge + "</div></div>";
      }).join("") + "</div>" +
      '<div class="q-actions" style="margin-top:16px"><button class="btn-primary" id="p1-begin">' +
        icon('<path d="M6 4l14 8-14 8z" fill="currentColor" stroke="none"/>') + " Begin practice · " + CASES.length + " cases</button>" +
        '<span class="pts">Each case: diagnostic quality → error → cause → correction → comparison. ' + TOTAL_PTS + " points.</span></div></div>";
    document.getElementById("p1-begin").addEventListener("click", function () {
      state = { idx: 0, sub: 0 }; progress.style.display = "flex"; renderStep();
    });
    updateChrome();
  }

  // ---- STEP ----------------------------------------------------------------
  function renderStep() {
    var c = CASES[state.idx], step = c.steps[state.sub], rec = records[state.idx][state.sub];
    var at = (step.answer_type || "").toLowerCase();
    var isVisual = at.indexOf("visual") !== -1;
    var locked = rec != null;
    var complete = locked || isVisual;  // the visual-comparison step auto-completes
    var q = '<div class="p4-q"><div class="p4-qhead"><span class="keyline"></span>' +
      '<span class="qstep">Step ' + step.n + " · " + (STEP_LABEL[step.key] || step.key) + "</span>" +
      '<span class="objtag"><span class="mastery">Obj ' + step.objective + "</span></span></div>" +
      '<div class="p4-qbody"><div class="p4-prompt">' + esc(step.prompt) + "</div>";

    if (at.indexOf("visual") !== -1) {
      q += '<div class="correct-line">' + I_CHECK.replace('stroke="currentColor"', 'stroke="var(--action)"') +
        "<span>Expected outcome · <b>" + esc(step.expected) + "</b></span></div>" +
        '<div class="compare"><div class="pane"><div class="plab">Original · non-diagnostic</div><div class="pimg">' +
          icon('<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M8 4v16M12 4v16"/>', 1.3).replace('width="16" height="16"', 'width="26" height="26"') + "</div></div>" +
        '<div class="pane"><div class="plab">Corrected · diagnostic</div><div class="pimg">' +
          icon('<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 4v16M11 4v16M15 4v16"/>', 1.3).replace('width="16" height="16"', 'width="26" height="26"') + "</div></div></div>" +
        '<div class="step-foot">' + icon('<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h.01"/>') +
          '<div class="fb"><b>Feedback:</b> ' + esc(step.feedback) + (c.pearl ? " · <span style=\"font-style:normal\">" + esc(c.pearl) + "</span>" : "") + "</div></div>";
      if (!locked) records[state.idx][state.sub] = { reviewed: true, ok: true };
    } else {
      var chosen = rec && rec.chosen;
      if (locked) q += '<div class="correct-line">' + I_CHECK.replace('stroke="currentColor"', 'stroke="var(--action)"') + "<span>Correct answer · <b>" + esc(step.expected) + "</b></span></div>";
      var two = step.options.length === 2 ? ' choices--two' : '';
      q += choicesHTML(step.options, step.expected, chosen, locked).replace('class="choices"', 'class="choices' + two + '"');
      if (locked) q += feedbackHTML(rec.ok, step.feedback);
    }

    if (complete) {
      var last = state.idx === CASES.length - 1 && state.sub === c.steps.length - 1;
      var lastInCase = state.sub === c.steps.length - 1;
      q += '<div class="q-actions"><span class="spacer"></span><button class="btn-primary" id="next">' +
        (last ? "See results " + I_ARROW : lastInCase ? "Next case " + I_ARROW : "Continue " + I_ARROW) + "</button></div>";
    }
    q += "</div></div>";

    app.innerHTML = '<div class="p4-body">' + filmHTML(c) + '<div id="qcol">' + q + "</div></div>";
    wireStep();
    updateChrome();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function wireStep() {
    var c = CASES[state.idx], step = c.steps[state.sub];
    document.querySelectorAll(".choice:not([disabled]), .binary .btn:not([disabled])").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var opt = btn.getAttribute("data-opt");
        records[state.idx][state.sub] = { chosen: opt, ok: isCorrect(opt, step.expected) };
        renderStep();
      });
    });
    var next = document.getElementById("next");
    if (next) next.addEventListener("click", advance);
  }

  function advance() {
    var c = CASES[state.idx];
    if (state.sub < c.steps.length - 1) { state.sub += 1; renderStep(); }
    else if (state.idx < CASES.length - 1) { state.idx += 1; state.sub = 0; renderStep(); }
    else renderSummary();
  }

  // ---- SUMMARY -------------------------------------------------------------
  function renderSummary() {
    progress.style.display = "none";
    var n = CASES.length;
    function keyStats(key) {
      var ok = 0, of = 0;
      CASES.forEach(function (c, ci) {
        var si = c.steps.findIndex(function (s) { return s.key === key; });
        if (si >= 0) { of++; if (records[ci][si] && records[ci][si].ok) ok++; }
      });
      return { ok: ok, of: of };
    }
    var diag = keyStats("diagnostic"), err = keyStats("error"), cause = keyStats("cause"), corr = keyStats("correction");
    var score = earned();
    var objRes = {
      1: { hit: diag.ok, of: diag.of, note: "Diagnostic vs non-diagnostic classifications" },
      2: { hit: err.ok, of: err.of, note: "Radiographic errors correctly identified" },
      3: { hit: cause.ok, of: cause.of, note: "Most-likely causes correctly determined" },
      4: { hit: corr.ok, of: corr.of, note: "Correct corrective actions selected" },
      5: { hit: diag.ok, of: diag.of, note: "Retake-required cases correctly flagged" },
      6: { hit: n, of: n, note: "Original vs corrected comparisons reviewed" }
    };
    function tile(num, cap, note) { return '<div class="kpi-tile"><div class="kpi-num tabular">' + num + '</div><div class="kpi-cap">' + cap + '</div><div class="kpi-note">' + note + "</div></div>"; }
    var pctErr = err.of ? Math.round((err.ok / err.of) * 100) : 0;
    var rows = OBJ.map(function (o) {
      var res = objRes[o.n]; var hit = res.hit >= res.of;
      return '<div class="sum-obj"><div class="ic ' + (hit ? "hit" : "miss") + '">' + (hit ? "✓" : "!") + "</div>" +
        '<div><div class="st">' + esc(o.text) + ' <b class="tabular">' + res.hit + " / " + res.of + "</b></div>" +
        '<div class="sd">' + esc(res.note) + "</div></div></div>";
    }).join("");
    app.innerHTML =
      '<div class="section-banner" style="margin-top:4px"><span class="section-kicker">Results</span><h2>Module 1 · Session Summary</h2><span class="sub">' + n + " cases completed</span></div>" +
      '<div class="sum-tiles">' +
        tile(score + " / " + TOTAL_PTS, "Score", "1 + 2 + 2 + 2 pts per case") +
        tile(pctErr + "%", "Error-ID accuracy", err.ok + " of " + err.of + " correct") +
        tile(diag.ok + " / " + diag.of, "Diagnostic calls", "Diagnostic vs non-diagnostic") +
        tile(corr.ok + " / " + corr.of, "Corrections", "Right fix selected") +
      "</div>" +
      '<div class="grid-2"><div class="card"><div class="card-head"><span class="keyline"></span><h3>Objective coverage</h3></div><div>' + rows + "</div></div>" +
      '<div style="display:flex;flex-direction:column;gap:12px">' +
        '<div class="callout">' + icon('<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M8 12h8M8 8h8M8 16h5"/>') +
          '<div class="ct"><b>Full error-correction reasoning chain.</b> For every case you classified diagnostic quality, named the error, traced its cause, and chose the corrective action — the Module 1 workflow.</div></div>' +
        '<div class="card"><div class="card-body" style="display:flex;gap:8px;align-items:center"><button class="btn-primary" id="restart">' +
          icon('<path d="M3 2v6h6"/><path d="M3 8a9 9 0 1 0 3-6.7L3 8"/>') + ' Restart Module 1</button><a class="btn-ghost" href="/module/1">Back to Module 1</a></div></div>' +
      "</div></div>";
    document.getElementById("restart").addEventListener("click", function () { reset(); renderIntro(); });
    updateChrome();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  reset();
  renderIntro();
})();
```

For reference, the original page shell (Jinja) — its storyboard block is what
the #storyboard slot content translates:

```jinja
{% extends "base.html" %}
{% from "_icons.html" import icon %}
{% from "_macros.html" import sb_row %}
{% block title %}Module 1 Practice · Image Quality &amp; Error Correction — {{ platform.name }}{% endblock %}

{% block storyboard %}
  <div class="sb-eyebrow">Module 1 · Practice</div>
  <div class="sb-title">{{ m1.module.title }}</div>
  <div class="sb-goal">{{ m1.module.goal }}</div>
  <div class="sb-div"></div>
  {{ sb_row('layers', 'Error cases', m1.cases | length) }}
  <div class="sb-row"><span class="glyph">{{ icon('target', 16) }}</span><div><div class="sb-fl">Session score</div><div class="sb-fv" id="sb-score">0 / {{ m1.total_points }} pts</div></div></div>
  <div class="sb-row"><span class="glyph">{{ icon('check', 16) }}</span><div><div class="sb-fl">Diagnostic calls</div><div class="sb-fv" id="sb-acc">—</div></div></div>
  <div class="sb-div"></div>
  <div class="sb-fl" style="margin-bottom:8px">Cases</div>
  <div id="sb-caselist">
    {% for c in m1.cases %}
    <div class="sb-plain-item" data-caseidx="{{ loop.index0 }}">
      <div class="sb-li-id">{{ c.id }}</div>
      <div class="sb-li-name">{{ c.name }}</div>
    </div>
    {% endfor %}
  </div>
{% endblock %}

{% block content %}
<div class="crumbs">
  <a href="{{ url_for('overview') }}">Overview</a><span class="sep">›</span>
  <a href="{{ url_for('module', number=1) }}">Module 1</a><span class="sep">›</span>Practice
</div>

<div class="section-banner">
  <span class="section-kicker">Module 1 · Practice</span>
  <h2>Image Quality &amp; Error Correction</h2>
  <span class="sub">Diagnostic quality → error → cause → correction → comparison</span>
</div>

<div class="p4-progresswrap" id="p1-progress" style="display:none">
  <span class="lab" id="p1-lab">Case 1 of {{ m1.cases | length }}</span>
  <div class="bar"><span id="p1-bar" style="width:0%"></span></div>
  <span class="lab" id="p1-score">0 pts</span>
</div>

<div id="p1-app"><!-- rendered by module1.js --></div>

<script type="application/json" id="m1-data">{{ m1 | tojson }}</script>
{% endblock %}

{% block scripts %}
<script src="{{ url_for('static', filename='js/module1.js') }}"></script>
{% endblock %}
```

## Trainer CSS (append once to OrbitShell.vue's non-scoped style block)

```css
.p4-progresswrap{display:flex; align-items:center; gap:12px; margin-bottom:12px}
.p4-progresswrap .bar{flex:1 1 auto; height:8px; background:var(--header-gray); border-radius:4px; overflow:hidden}
.p4-progresswrap .bar>span{display:block; height:100%; background:var(--action); transition:width .35s ease}
.p4-progresswrap .lab{font-size:12px; font-weight:600; color:var(--muted); white-space:nowrap; font-variant-numeric:tabular-nums}

.p4-hero{background:var(--card); border:1px solid var(--border); border-radius:var(--r-card); box-shadow:var(--shadow-card); padding:20px 22px; margin-bottom:12px}
.p4-hero h1{font-size:20px; margin:0 0 4px; color:var(--ink)}
.p4-hero .lead{font-size:13px; color:var(--muted); max-width:70ch; line-height:1.5}
.obj-grid{display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:14px}
@media(max-width:760px){.obj-grid{grid-template-columns:1fr}}
.obj-card{display:flex; gap:10px; padding:10px 12px; border:1px solid var(--border); border-radius:var(--r-card); background:var(--zebra)}
.obj-card .n{flex:0 0 22px; height:22px; border-radius:50%; background:var(--slate); color:#fff; display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:700}
.obj-card .t{font-size:12px; color:var(--ink); line-height:1.4}
.obj-card .mastery{margin-top:5px}

.p4-body{display:grid; grid-template-columns:minmax(340px,1fr) minmax(360px,1fr); gap:12px; align-items:start}
@media(max-width:980px){.p4-body{grid-template-columns:1fr}}
.p4-view{background:var(--card); border:1px solid var(--border); border-radius:var(--r-card); box-shadow:var(--shadow-card); overflow:hidden; position:sticky; top:60px}
@media(max-width:980px){.p4-view{position:static}}
.p4-view .imgwrap{position:relative; background:#0c0f13}
.p4-view img{display:block; width:100%; height:auto}
.roi{position:absolute; border:2px solid #ffd23f; border-radius:50%; box-shadow:0 0 0 2px rgba(0,0,0,.35), 0 0 12px rgba(255,210,63,.6);
  transform:translate(-50%,-50%); pointer-events:none; animation:roipulse 1.8s ease-in-out infinite}
@keyframes roipulse{0%,100%{opacity:.55} 50%{opacity:1}}
.p4-view .vcap{padding:8px 12px; border-top:1px solid var(--border)}
.p4-view .vcap .roinote{font-size:10px; color:var(--muted); text-transform:uppercase; letter-spacing:.04em}
.p4-view .vcap .finding{font-size:13px; color:var(--ink); margin-top:4px; line-height:1.45}
.feat-list{list-style:none; margin:8px 0 0; padding:8px 12px 12px; border-top:1px solid var(--cell-sep)}
.feat-list li{font-size:12px; color:var(--muted); padding-left:16px; position:relative; margin-bottom:4px}
.feat-list li::before{content:""; position:absolute; left:2px; top:6px; width:6px; height:6px; border-radius:50%; background:var(--action)}

.p4-q{background:var(--card); border:1px solid var(--border); border-radius:var(--r-card); box-shadow:var(--shadow-card); overflow:hidden}
.p4-qhead{display:flex; align-items:center; gap:8px; padding:10px 14px; border-bottom:1px solid var(--cell-sep)}
.p4-qhead .keyline{width:3px; height:16px; background:var(--action); border-radius:2px}
.p4-qhead .qstep{font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--muted)}
.p4-qhead .objtag{margin-left:auto}
.p4-qbody{padding:14px}
.p4-prompt{font-size:14px; font-weight:600; color:var(--ink); margin-bottom:10px}
.p4-sub{font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:.03em; color:var(--muted); margin-bottom:6px}
.choice{display:flex; align-items:center; gap:10px; width:100%; text-align:left; padding:11px 12px; margin-bottom:8px;
  border:1px solid var(--border); border-radius:var(--r-card); font-size:13px; color:var(--ink); background:#fff; cursor:pointer; font-family:inherit; transition:border-color .1s, background .1s}
.choice:hover:not(:disabled){border-color:var(--action); background:var(--zebra)}
.choice .mark{flex:0 0 16px; width:16px; height:16px; border-radius:50%; border:1.5px solid #B7C0C9; display:flex; align-items:center; justify-content:center}
.choice .txt{flex:1 1 auto}
.choice .tag{flex:0 0 auto; font-size:11px; font-weight:700}
.choice.selected{border-color:var(--action)}
.choice.correct{background:var(--good-fill); border-color:var(--good-border)}
.choice.correct .mark{border-color:var(--good-border); background:var(--good-border); color:#fff}
.choice.correct .tag{color:var(--good-text)}
.choice.wrong{background:var(--bad-fill); border-color:var(--bad-border)}
.choice.wrong .mark{border-color:var(--bad-border); background:var(--bad-border); color:#fff}
.choice.wrong .tag{color:var(--bad-text)}
.choice.muted{opacity:.55}
.choice:disabled{cursor:default}
.choices--two{display:grid; grid-template-columns:1fr 1fr; gap:8px}
.choices--two .choice{margin-bottom:0}

.feedback{margin-top:10px; padding:11px 12px; border-radius:var(--r-card); font-size:13px; line-height:1.5; border:1px solid}
.feedback.ok{background:var(--good-fill); border-color:var(--good-border); color:var(--good-text)}
.feedback.no{background:var(--bad-fill); border-color:var(--bad-border); color:var(--bad-text)}
.feedback b{font-weight:700}
.feedback .lead{display:flex; align-items:center; gap:6px; font-weight:700; margin-bottom:4px}

.confidence{display:flex; align-items:center; gap:10px; margin:10px 0 4px}
.confidence label{font-size:12px; color:var(--muted); margin-bottom:0}
.confidence input[type=range]{flex:1 1 auto; accent-color:var(--action)}
.confidence .val{font-size:12px; font-weight:700; color:var(--ink); width:52px; text-align:right}

.q-actions{display:flex; gap:8px; align-items:center; margin-top:12px}
.q-actions .spacer{flex:1}
.btn-primary{display:inline-flex; align-items:center; gap:8px; font-size:13px; font-weight:600; color:#fff;
  background:var(--action); border:1px solid var(--action); border-radius:var(--r-card); padding:9px 16px;
  text-decoration:none; cursor:pointer; font-family:inherit}
.btn-primary:hover{background:var(--action-hover); border-color:var(--action-hover); color:#fff}
.btn-ghost{display:inline-flex; align-items:center; gap:8px; font-size:13px; font-weight:600; color:var(--action);
  background:#fff; border:1px solid var(--border); border-radius:var(--r-card); padding:9px 16px; text-decoration:none; cursor:pointer; font-family:inherit}
.btn-ghost:hover{border-color:var(--action)}

.tutor{margin-top:12px; border:1px solid var(--ai-border); border-radius:var(--r-card); overflow:hidden; background:#fff}
.tutor-head{display:flex; align-items:center; gap:8px; padding:8px 12px; background:var(--ai-fill); border-bottom:1px solid var(--ai-border)}
.tutor-head .t{font-size:12px; font-weight:700; color:var(--ai-text)}
.tutor-head .st{margin-left:auto; font-size:10px; color:var(--muted); text-transform:uppercase; letter-spacing:.04em}
.tutor-log{padding:12px; display:flex; flex-direction:column; gap:8px; max-height:280px; overflow-y:auto}
.msg{display:flex; gap:8px; max-width:92%}
.msg .who{flex:0 0 26px; width:26px; height:26px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:10px; font-weight:700; color:#fff}
.msg .bub{padding:8px 11px; border-radius:10px; font-size:13px; line-height:1.45}
.msg.ai{align-self:flex-start}
.msg.ai .who{background:var(--action)}
.msg.ai .bub{background:var(--ai-fill); color:var(--ink); border:1px solid #cfe4f6}
.msg.me{align-self:flex-end; flex-direction:row-reverse}
.msg.me .who{background:var(--slate)}
.msg.me .bub{background:var(--slate); color:#fff}
.msg.think .bub{color:var(--muted); font-style:italic}
.tutor-in{display:flex; gap:8px; padding:10px 12px; border-top:1px solid var(--cell-sep)}
.tutor-in input{flex:1 1 auto; font-family:inherit; font-size:13px; padding:8px 10px; border:1px solid var(--border); border-radius:var(--r-card)}
.tutor-in input:focus{outline:2px solid var(--action); outline-offset:-1px}

.sum-tiles{display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:12px}
@media(max-width:760px){.sum-tiles{grid-template-columns:repeat(2,1fr)}}
.sum-obj{display:flex; gap:10px; align-items:flex-start; padding:10px 12px; border-bottom:1px solid var(--cell-sep)}
.sum-obj:last-child{border-bottom:0}
.sum-obj .ic{flex:0 0 20px; height:20px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:11px; color:#fff}
.sum-obj .ic.hit{background:var(--good-border)}
.sum-obj .ic.miss{background:#B7C0C9}
.sum-obj .st{font-size:13px; color:var(--ink); line-height:1.4}
.sum-obj .sd{font-size:11px; color:var(--muted); margin-top:2px}

.p1-film{position:relative; aspect-ratio:4/3; background:radial-gradient(ellipse at center,#2b3440 0%,#171c22 100%);
  display:flex; flex-direction:column; align-items:center; justify-content:center; gap:10px; color:#7d8b99}
.p1-mod{font-size:12px; font-weight:600; letter-spacing:.04em; color:#9aa7b4; text-transform:uppercase}
.p1-corner{position:absolute; width:14px; height:14px; border:2px solid rgba(255,255,255,.14)}
.p1-corner.tl{top:8px; left:8px; border-right:0; border-bottom:0}
.p1-corner.tr{top:8px; right:8px; border-left:0; border-bottom:0}
.p1-corner.bl{bottom:8px; left:8px; border-right:0; border-top:0}
.p1-corner.br{bottom:8px; right:8px; border-left:0; border-top:0}

.m5-clickable{cursor:crosshair}
.m5-marker{position:absolute; width:26px; height:26px; margin:-13px 0 0 -13px; border:2px solid #ffd23f;
  border-radius:50%; box-shadow:0 0 0 2px rgba(0,0,0,.35),0 0 12px rgba(255,210,63,.6)}
.m5-hint{position:absolute; bottom:10px; left:0; right:0; text-align:center; font-size:11px; color:#9aa7b4}
.ai-panel{display:flex; gap:10px; align-items:flex-start; padding:11px 12px; margin-bottom:10px;
  background:var(--ai-fill); border:1px solid var(--ai-border); border-radius:var(--r-card)}
.ai-lab{font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:var(--ai-text)}
.ai-txt{font-size:13px; color:var(--ink); margin-top:3px; line-height:1.45}

.sb-list-item{display:block; text-decoration:none; background:var(--slate-alt); border-left:3px solid var(--action);
  padding:8px 10px; margin:0 -14px 6px}
.sb-list-item .sb-li-id{color:#fff}
```

## Hard constraints

- Plain JavaScript, `<script setup>`, 2-space indent, single quotes. No
  TypeScript, no new npm packages, no icon libraries.
- Do not touch: env SCSS files, main.js, vite.config.js, package.json, anything
  under src/app/, OrbitNavbar.vue, App.vue, publicRoutes, existing demo
  components, or the Phase 3 page components other than the OrbitModule.vue
  edit described above.
- The word "Epic" must not appear anywhere.
- All existing routes keep working. Run `npm run build:dev` from src/frontend
  and confirm it passes.
- List every file created/changed with a one-line summary and stop. Do not
  commit or push.
