# Phase 3 prompt — five static ORBIT pages

## BEFORE running this prompt (manual step for Arjun, not for their Claude)

Copy `orbit_dashboard/data/orbit.json` from the Mac into their repo at:

    src/frontend/src/components/orbit/orbit-data.json

(Drag the file into the VS Code file tree on the dev box, then rename it.)
The prompt below makes their Claude verify the file exists before starting.

---
Paste everything below this line into their Claude.
---

We're on the `feature/new-ui-foundation` branch. Phases 1–2 of the ORBIT UI
migration are done (design tokens; OrbitShell + OrbitOverview at `/orbit`).
Now execute Phase 3: the five remaining static pages — Module Detail, Case
Library, Case Detail, Interaction Matrix, Reference — driven by a bundled JSON
data file. Everything stays additive; all existing routes and demos keep
working.

FIRST: verify `src/frontend/src/components/orbit/orbit-data.json` exists (I
placed it there manually). If it's missing, STOP and tell me — do not invent
data. Read it to learn the exact shapes; top-level keys: `platform`, `stats`,
`modules`, `cases`, `buildout`, `interaction`, `reference`.

## Files

Create (all under src/frontend/src/components/orbit/):
  orbitData.js        — imports orbit-data.json; exports the data plus helpers:
                        modulesByNum (Map/object), casesById, buildout.by_case
                        lookup, orderedModuleNumbers, DIFFICULTY constant:
                        {1:{label:'Obvious / basic'},2:{label:'Moderate'},3:{label:'Subtle / complex'}}
  DiffPill.vue        — props: level (Number), label (Boolean, default true).
                        Renders the difficulty pill:
                        <span :class="'pill pill--diff'+level">Diff {level} (or just {level} when label=false)
                          <span class="dots"><i v-for="i in 3" :class="['dot',{off:i>level}]"></i></span></span>
                        For level outside 1–3 render <span class="chip">—</span>.
  OrbitChip.vue       — props: text, kind ('', 'ai', 'future'). Renders
                        <span class="chip"> with chip--ai / chip--future modifier.
  OrbitModule.vue     — page, route /orbit/module/:number
  OrbitCases.vue      — page, route /orbit/cases
  OrbitCase.vue       — page, route /orbit/case/:id
  OrbitInteraction.vue — page, route /orbit/interaction
  OrbitReference.vue  — page, route /orbit/reference

Edit:
  src/frontend/src/router.js — add the five routes above (eager imports, all
    with `meta: { orbitShell: true }`, NONE added to publicRoutes):
      /orbit/module/:number → name 'orbit-module' (props: true)
      /orbit/cases          → name 'orbit-cases'
      /orbit/case/:id       → name 'orbit-case' (props: true)
      /orbit/interaction    → name 'orbit-interaction'
      /orbit/reference      → name 'orbit-reference'
  src/frontend/src/components/orbit/OrbitShell.vue —
    (a) tab strip: the four placeholder tabs become router-links —
        Modules → {name:'orbit-module', params:{number:4}}, Case Library →
        {name:'orbit-cases'}, Interaction Matrix → {name:'orbit-interaction'},
        Reference → {name:'orbit-reference'}; each gets tab--active when
        `activeTab` equals 'modules'/'cases'/'interaction'/'reference'.
    (b) sidebar: wrap the existing sidebar content in
        <slot name="storyboard"> ... </slot> so pages can replace it; the
        current content stays as the slot's default. In that default, the
        eight "Jump to module" items become router-links to
        {name:'orbit-module', params:{number:n}}.
    (c) append the "Phase 3 CSS additions" block (bottom of this prompt) to the
        existing non-scoped <style> block.
  src/frontend/src/components/orbit/OrbitOverview.vue — links only, data stays
    hardcoded: mod-mini cards → router-links to their module page; case-table
    rows clickable → router.push to the case page (add class "rowlink" is
    already on the tr styles; use @click) and the case id becomes a
    router-link with class "cid"; the "AI-comparison" callout stays as is.

## Source templates (Jinja) — translate these faithfully to Vue

These are the exact templates from the source app. Translation rules:
- `{% for %}` → v-for; `{% if %}` → v-if/ternaries; `{{ x }}` → {{ x }}.
- `url_for('module', number=n)` → router-link to orbit-module; `url_for('case',
  case_id=id)` → orbit-case; `url_for('cases')` → orbit-cases;
  `url_for('overview')` → {name:'orbit'}. `url_for('api_data')` (Export JSON
  link in cases.html) → drop that link entirely for now.
- `{{ icon(...) }}` macros → omit, or small decorative inline SVGs; never an
  icon library.
- `diff_pill(...)` → <DiffPill>, `chip(...)` → <OrbitChip>,
  `mastery(o)` → <span :class="['mastery',{'mastery--improve':o.kind==='improvement'}]">{{ o.target }}</span>
  (render only when o.target).
- `sb_row(icon,label,value)` → <div class="sb-row"><div><div class="sb-fl">label</div><div class="sb-fv">value</div></div></div>
- `rowlink` rows with onclick → keep class, use @click="router.push(...)".
- Each page renders inside <OrbitShell :active-tab="..."> and supplies
  <template #storyboard> translated from the template's `{% block storyboard %}`.
- The "Launch practice" button (module.html) — the practice routes don't exist
  yet (Phase 4). For modules 1, 3, 4, 5 render a disabled-looking
  <span class="chip">Practice · coming in Phase 4</span> where the button would
  be; for others follow the template's existing else-branches.
- Filters on the Case Library page: reactive refs instead of a form GET.
  Initialize the module filter from the route query (?module=N) so the
  module page's "Filter library" link (router-link with query {module: n})
  works; changing any filter just updates local refs and the computed rows —
  no navigation. "Clear" resets the refs.
- Case page derivations (from the source backend): steps =
  buildout.by_case[id] || []; total_points = sum of step.points; mod =
  modulesByNum[c.module]. Module page: prev/next from orderedModuleNumbers;
  difficulty range string = min–max of the module's cases' difficulties
  ('—' when no cases; single number when min==max).
- Interaction page rows: use data.interaction if non-empty, else flatten
  modules[].interaction. Sidebar "AI-measured" count = rows whose `measures`
  contains 'AI'.
- Unknown module number or case id in the URL → redirect to /404.

### module.html
```jinja
{% extends "base.html" %}
{% from "_icons.html" import icon %}
{% from "_macros.html" import diff_pill, chip, mastery, sb_row %}
{% block title %}Module {{ mod.number }} · {{ mod.title }} — {{ platform.name }}{% endblock %}

{% set diffs = mod.cases | map(attribute='difficulty') | select('number') | list %}
{% set dmin = diffs | min if diffs else None %}
{% set dmax = diffs | max if diffs else None %}
{% set drange = ('—' if dmin is none else (dmin|string if dmin == dmax else dmin|string ~ '–' ~ dmax|string)) %}

{% block storyboard %}
  <div class="sb-eyebrow">Module {{ mod.number }}</div>
  <div class="sb-title">{{ mod.title }}</div>
  <div class="sb-goal">{{ mod.description }}</div>
  {% if mod.ai_enabled %}
  <div class="sb-chip" style="margin-top:10px">{{ icon('ai', 12) }}&nbsp;AI dialogue · Built-in</div>
  {% endif %}
  {% if practice_url %}
  <a class="btn-primary" href="{{ practice_url }}" style="margin-top:12px; width:100%; justify-content:center">{{ icon('play', 14, '#fff') }} Launch practice</a>
  {% endif %}
  <div class="sb-div"></div>
  {{ sb_row('target', 'Objectives', mod.objective_count ~ ' measurable') }}
  {{ sb_row('layers', 'Authored cases', mod.case_count) }}
  {{ sb_row('grid', 'Activity steps', mod.authored_steps) }}
  {{ sb_row('image', 'Difficulty range', drange) }}
  {% if mod.cases %}
  <div class="sb-div"></div>
  <div class="sb-fl" style="margin-bottom:8px">Cases in module</div>
  {% for c in mod.cases %}
    <a class="sb-plain-item" href="{{ url_for('case', case_id=c.id) }}">
      <div class="sb-li-id">{{ c.id }}</div>
      <div class="sb-li-name">{{ c.name }}</div>
    </a>
  {% endfor %}
  {% endif %}
{% endblock %}

{% block content %}
<div class="crumbs"><a href="{{ url_for('overview') }}">Overview</a><span class="sep">›</span>Module {{ mod.number }}</div>

<div class="section-banner">
  <span class="section-kicker">Module Detail</span>
  <h2>Module {{ mod.number }} · {{ mod.title }}</h2>
  <span class="sub">{{ mod.objective_count }} objectives · {{ mod.case_count }} cases{% if mod.ai_enabled %} · AI dialogue{% endif %}</span>
</div>

<div class="mod-header">
  <div class="top">
    <span class="mnum">Module {{ mod.number }}</span>
    <h3>{{ mod.title }}</h3>
    {% if practice_url %}<a class="btn-primary" href="{{ practice_url }}" style="margin-left:auto">{{ icon('play', 14, '#fff') }} Launch practice</a>
    {% elif mod.ai_enabled %}<span class="chip chip--ai" style="margin-left:auto">AI-comparison · on</span>{% endif %}
  </div>
  <div class="goal-edit">
    {{ icon('edit', 16) }}
    <span>{{ mod.description }}</span>
  </div>
  {% if mod.note %}<div class="mod-note">Authoring note · <b>{{ mod.note }}</b></div>{% endif %}
  <div class="mod-kpis">
    <div class="mod-kpi"><div class="k tabular">{{ mod.objective_count }}</div><div class="l">Objectives</div></div>
    <div class="mod-kpi"><div class="k tabular">{{ mod.case_count }}</div><div class="l">Cases</div></div>
    <div class="mod-kpi"><div class="k tabular">{{ mod.authored_steps }}</div><div class="l">Activity Steps</div></div>
    <div class="mod-kpi"><div class="k">{{ drange }}</div><div class="l">Difficulty</div></div>
  </div>
</div>

<div class="grid-2">
  <div class="card">
    <div class="card-head"><span class="keyline"></span><h3>Learning Objectives</h3><div class="actions"><span class="pts">{{ mod.objective_count }} total</span></div></div>
    <div>
      {% for o in mod.objectives %}
      <div class="obj-row">
        <div class="obj-num tabular">{{ o.n }}</div>
        <div class="obj-body">
          <div class="obj-text">{{ o.text }}</div>
          {% if o.target %}<div class="obj-meta">{{ mastery(o) }}<span class="qt">{{ 'Improvement after AI dialogue' if o.kind == 'improvement' else 'Mastery threshold' }}</span></div>{% endif %}
        </div>
      </div>
      {% endfor %}
    </div>
  </div>

  <div class="card">
    <div class="card-head"><span class="keyline"></span><h3>Cases in Module {{ mod.number }}</h3><div class="actions"><a class="link" href="{{ url_for('cases', module=mod.number) }}">Filter library</a></div></div>
    {% if mod.cases %}
    <div class="grid-wrap">
      <table class="data-grid tight">
        <thead><tr><th>Case</th><th>Type</th><th class="num">Diff</th></tr></thead>
        <tbody>
          {% for c in mod.cases %}
          <tr class="rowlink" onclick="location.href='{{ url_for('case', case_id=c.id) }}'">
            <td><a class="cid" href="{{ url_for('case', case_id=c.id) }}">{{ c.id }}</a><div class="cname">{{ c.name }}</div></td>
            <td>{{ chip(c.type) }}</td>
            <td class="num">{{ diff_pill(c.difficulty, label=False) }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    {% else %}
    <div class="empty">{{ icon('layers', 26) }}<div class="et">No cases authored yet</div><div class="es">This module's case library is still being built out.</div></div>
    {% endif %}

    {% if mod.interaction %}
    <div class="card-head" style="border-top:1px solid var(--border)"><span class="keyline"></span><h3>Interaction Design · scoped</h3></div>
    <div class="grid-wrap">
      <table class="data-grid tight">
        <thead><tr><th>Obj</th><th>Question Type</th><th>What we measure</th></tr></thead>
        <tbody>
          {% for r in mod.interaction %}
          <tr><td class="num tabular">{{ r.objective }}</td><td>{{ r.question_type }}</td><td class="notes" title="{{ r.measures }}">{{ r.measures }}</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    {% endif %}
  </div>
</div>

<div class="mod-nav">
  {% if prev_num %}<a href="{{ url_for('module', number=prev_num) }}">{{ icon('arrow-left', 14) }} Module {{ prev_num }}</a>{% else %}<span></span>{% endif %}
  <span class="spacer"></span>
  {% if next_num %}<a href="{{ url_for('module', number=next_num) }}">Module {{ next_num }} {{ icon('arrow-right', 14) }}</a>{% endif %}
</div>
{% endblock %}
```

### cases.html
```jinja
{% extends "base.html" %}
{% from "_icons.html" import icon %}
{% from "_macros.html" import diff_pill, chip, sb_row %}
{% block title %}Case Library — {{ platform.name }}{% endblock %}

{% block storyboard %}
  <div class="sb-eyebrow">Case Library</div>
  <div class="sb-title">Authored Cases</div>
  <div class="sb-goal">Every case is an expert-labeled radiograph with a multi-step activity.</div>
  <div class="sb-div"></div>
  {{ sb_row('grid', 'Total cases', stats.cases) }}
  {{ sb_row('layers', 'Case types', case_types | length) }}
  {{ sb_row('image', 'Showing', rows | length) }}
  <div class="sb-div"></div>
  <div class="sb-fl" style="margin-bottom:8px">Difficulty legend</div>
  {% for d in stats.difficulty_distribution %}
  <div class="sb-row" style="margin-bottom:10px">
    <span style="flex:0 0 auto">{{ diff_pill(d.level, label=False) }}</span>
    <div><div class="sb-fv" style="margin-top:0">{{ d.label }}</div><div class="sb-fl">{{ d.count }} cases</div></div>
  </div>
  {% endfor %}
{% endblock %}

{% block content %}
<div class="crumbs"><a href="{{ url_for('overview') }}">Overview</a><span class="sep">›</span>Case Library</div>

<div class="section-banner">
  <span class="section-kicker">Case Library</span>
  <h2>All Authored Cases</h2>
  <span class="sub">{{ total }} cases · filter by module, type &amp; difficulty</span>
</div>

<form class="filter-bar" method="get" action="{{ url_for('cases') }}">
  <span class="fl">{{ icon('sliders', 14, 'var(--muted)') }} Filters</span>
  <label>Module
    <select name="module" onchange="this.form.submit()">
      <option value="">All</option>
      {% for m in modules_with_cases %}
      <option value="{{ m }}" {{ 'selected' if f_module == m }}>Module {{ m }}</option>
      {% endfor %}
    </select>
  </label>
  <label>Difficulty
    <select name="difficulty" onchange="this.form.submit()">
      <option value="">All</option>
      {% for lvl in [1,2,3] %}
      <option value="{{ lvl }}" {{ 'selected' if f_diff == lvl }}>{{ DIFFICULTY[lvl].label }}</option>
      {% endfor %}
    </select>
  </label>
  <label>Case type
    <select name="type" onchange="this.form.submit()">
      <option value="">All</option>
      {% for t in case_types %}
      <option value="{{ t }}" {{ 'selected' if f_type == t }}>{{ t }}</option>
      {% endfor %}
    </select>
  </label>
  {% if f_module or f_diff or f_type %}<a class="link" href="{{ url_for('cases') }}">Clear</a>{% endif %}
  <span class="count"><b>{{ rows | length }}</b> of {{ total }} cases</span>
</form>

<div class="card">
  <div class="card-head"><span class="keyline"></span><h3>Case Library</h3>
    <div class="actions"><a class="link" href="{{ url_for('api_data') }}">Export JSON</a></div>
  </div>
  {% if rows %}
  <div class="grid-wrap">
    <table class="data-grid" style="min-width:1000px">
      <thead>
        <tr>
          <th>Case ID <span class="caret active">▲</span></th>
          <th class="num">Module</th>
          <th>Case Name</th>
          <th>Case Type</th>
          <th>Difficulty</th>
          <th>Ground Truth</th>
          <th>Question Type</th>
          <th class="num">Steps</th>
          <th>Notes</th>
        </tr>
      </thead>
      <tbody>
        {% for c in rows %}
        <tr class="rowlink" onclick="location.href='{{ url_for('case', case_id=c.id) }}'">
          <td><a class="cid" href="{{ url_for('case', case_id=c.id) }}">{{ c.id }}</a></td>
          <td class="num tabular">{{ c.module }}</td>
          <td class="cname">{{ c.name }}</td>
          <td>{{ chip(c.type) }}</td>
          <td>{{ diff_pill(c.difficulty) }}</td>
          <td>{{ c.ground_truth }}</td>
          <td>{{ c.question_type }}</td>
          <td class="num tabular">{{ c.steps }}</td>
          <td class="notes" title="{{ c.notes }}">{{ c.notes or '—' }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% else %}
  <div class="empty">{{ icon('grid', 26) }}<div class="et">No cases match these filters</div><div class="es"><a class="link" href="{{ url_for('cases') }}">Clear filters</a> to see all {{ total }} cases.</div></div>
  {% endif %}
</div>
{% endblock %}
```

### case.html
```jinja
{% extends "base.html" %}
{% from "_icons.html" import icon %}
{% from "_macros.html" import diff_pill, chip, sb_row %}
{% block title %}{{ c.id }} · {{ c.name }} — {{ platform.name }}{% endblock %}

{% block storyboard %}
  <div class="sb-eyebrow">Case {{ c.id }}</div>
  <div class="sb-title">{{ c.name }}</div>
  {% if mod %}<a class="sb-goal" style="text-decoration:none; display:block" href="{{ url_for('module', number=mod.number) }}">Module {{ mod.number }} · {{ mod.title }}</a>{% endif %}
  <div class="sb-div"></div>
  <div class="sb-row" style="margin-bottom:12px"><span style="flex:0 0 auto">{{ diff_pill(c.difficulty) }}</span></div>
  {{ sb_row('layers', 'Case type', c.type) }}
  {{ sb_row('target', 'Ground truth', c.ground_truth) }}
  {{ sb_row('info', 'Question type', c.question_type) }}
  {{ sb_row('grid', 'Activity steps', c.steps if c.steps else 'Not authored') }}
  {% if c.steps %}{{ sb_row('check', 'Points', total_points) }}{% endif %}
  {% if c.notes %}
  <div class="sb-div"></div>
  <div class="sb-fl" style="margin-bottom:6px">Notes</div>
  <div class="sb-goal">{{ c.notes }}</div>
  {% endif %}
{% endblock %}

{% block content %}
<div class="crumbs">
  <a href="{{ url_for('overview') }}">Overview</a><span class="sep">›</span>
  {% if mod %}<a href="{{ url_for('module', number=mod.number) }}">Module {{ mod.number }}</a><span class="sep">›</span>{% endif %}
  <a href="{{ url_for('cases') }}">Case Library</a><span class="sep">›</span>{{ c.id }}
</div>

<div class="section-banner">
  <span class="section-kicker">Case Activity</span>
  <h2>{{ c.id }} · {{ c.name }}</h2>
  <span class="sub">{% if c.steps %}CaseBuildout · {{ c.steps }} steps · {{ total_points }} pts{% else %}Metadata only{% endif %}</span>
</div>

<div class="activity-head">
  <div class="top">
    <span class="cid" style="font-size:13px">{{ c.id }}</span>
    <h3>{{ c.name }}</h3>
    {% if mod %}<span class="pts" style="margin-left:auto">Module {{ mod.number }} · {{ mod.title }}</span>{% endif %}
  </div>
  <div class="id-chips">
    {{ chip('Type · ' ~ c.type) }}
    {{ diff_pill(c.difficulty) }}
    {{ chip('Ground truth · ' ~ c.ground_truth) }}
    {{ chip('Question · ' ~ c.question_type) }}
    {% if mod and mod.ai_enabled %}{{ chip('AI dialogue', 'ai') }}{% endif %}
  </div>
</div>

{% if steps %}
<div class="activity-body">
  <div class="viewer">
    <div class="xray">
      {{ icon('xray', 34, '#9AA7B4', 1.3) }}
      <div class="cap">Radiograph · {{ c.id }}</div>
      <div class="cap" style="font-size:10px">{{ c.ground_truth }}</div>
    </div>
    <div class="viewer-foot"><span class="tot">Total available</span><span class="tot"><b class="tabular">{{ total_points }}</b> pts</span></div>
  </div>

  <div class="stepper">
    {% for s in steps %}
    {% set at = (s.answer_type or '')|lower %}
    {% set ca = (s.correct_answer or '')|lower|trim %}
    <div class="step">
      <div class="step-top">
        <div class="step-no">{{ s.step }}</div>
        <div class="step-prompt">{{ s.prompt }}</div>
        <div class="step-tags">{{ chip(s.answer_type) }}<span class="pts">{{ s.points }} pt{{ '' if s.points == 1 else 's' }}</span></div>
      </div>
      <div class="step-body">
        {% if 'binary' in at %}
          <div class="binary">
            {% for opt in s.answer_options %}
            {% set oc = opt|lower|trim %}
            {% set correct = oc and ((' ' ~ oc ~ ' ') in (' ' ~ ca ~ ' ')) %}
            <div class="btn {{ 'correct' if correct }}">{{ opt }}{{ ' ✓' if correct }}</div>
            {% endfor %}
          </div>
        {% elif 'visual' in at or not s.answer_options %}
          <div class="correct-line">{{ icon('check', 14, 'var(--action)', 2) }}<span>Expected outcome · <b>{{ s.correct_answer }}</b></span></div>
          <div class="compare">
            <div class="pane"><div class="plab">Original</div><div class="pimg">{{ icon('image', 26, '#9AA7B4', 1.3) }}</div></div>
            <div class="pane"><div class="plab">Corrected</div><div class="pimg">{{ icon('image', 26, '#9AA7B4', 1.3) }}</div></div>
          </div>
        {% else %}
          <div class="correct-line">{{ icon('check', 14, 'var(--action)', 2) }}<span>Correct answer · <b>{{ s.correct_answer }}</b></span></div>
          <div class="opts">
            {% for opt in s.answer_options %}
            {% set oc = opt|lower|trim %}
            {% set correct = oc and ((' ' ~ oc ~ ' ') in (' ' ~ ca ~ ' ')) %}
            <div class="opt {{ 'correct' if correct }}"><span class="radio"></span>{{ opt }}{% if correct %}<span class="ck">Correct ✓</span>{% endif %}</div>
            {% endfor %}
          </div>
        {% endif %}

        {% if s.feedback or s.data_captured %}
        <div class="step-foot">
          {{ icon('info', 14, 'var(--muted)', 1.6) }}
          <div class="fb">
            {% if s.feedback %}<b>Feedback:</b> {{ s.feedback }}{% endif %}
            {% if s.data_captured %}{% if s.feedback %} · {% endif %}<span style="font-style:normal">Captures: {{ s.data_captured }}</span>{% endif %}
          </div>
        </div>
        {% endif %}
      </div>
    </div>
    {% endfor %}
  </div>
</div>
{% else %}
<div class="card">
  <div class="empty">
    {{ icon('edit', 28) }}
    <div class="et">Interactive activity not yet authored</div>
    <div class="es">This case has its metadata and ground truth defined, but its step-by-step CaseBuildout flow hasn't been written yet.</div>
    <div style="margin-top:12px">{% if mod %}<a class="link" href="{{ url_for('module', number=mod.number) }}">← Back to Module {{ mod.number }}</a>{% endif %}</div>
  </div>
</div>
{% endif %}
{% endblock %}
```

### interaction.html
```jinja
{% extends "base.html" %}
{% from "_icons.html" import icon %}
{% from "_macros.html" import chip, sb_row %}
{% block title %}Interaction Matrix — {{ platform.name }}{% endblock %}

{% block storyboard %}
  {% set ns = namespace(ai=0) %}
  {% for r in rows %}{% if 'AI' in (r.measures or '') %}{% set ns.ai = ns.ai + 1 %}{% endif %}{% endfor %}
  <div class="sb-eyebrow">Interaction</div>
  <div class="sb-title">Interaction Design</div>
  <div class="sb-goal">How each objective is assessed — question type, student action, and what is measured.</div>
  <div class="sb-div"></div>
  {{ sb_row('sliders', 'Mapped rows', rows | length) }}
  {{ sb_row('target', 'Objectives', stats.objectives) }}
  {{ sb_row('ai', 'AI-measured', ns.ai) }}
{% endblock %}

{% block content %}
<div class="crumbs"><a href="{{ url_for('overview') }}">Overview</a><span class="sep">›</span>Interaction Matrix</div>

<div class="section-banner">
  <span class="section-kicker">Interaction Matrix</span>
  <h2>Question Design by Objective</h2>
  <span class="sub">{{ rows | length }} mapped interactions</span>
</div>

<div class="card">
  <div class="card-head"><span class="keyline"></span><h3>Interaction Design</h3></div>
  <div class="grid-wrap">
    <table class="data-grid" style="min-width:900px">
      <thead>
        <tr><th class="num">Module</th><th class="num">Obj</th><th>Question Type</th><th>Student Action</th><th>Input Type</th><th>Answer Type</th><th>What We Measure</th></tr>
      </thead>
      <tbody>
        {% for r in rows %}
        <tr {% if r.module and r.module|string in ['1','2','3','4','5','6','7','8'] %}class="rowlink" onclick="location.href='{{ url_for('module', number=r.module|int) }}'"{% endif %}>
          <td class="num tabular">{{ r.module }}</td>
          <td class="num tabular">{{ r.objective }}</td>
          <td>{{ chip(r.question_type) }}</td>
          <td>{{ r.student_action }}</td>
          <td>{{ r.input_type }}</td>
          <td>{{ r.correct_answer_type }}</td>
          <td class="cname">{{ r.measures }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
```

### reference.html
```jinja
{% extends "base.html" %}
{% from "_icons.html" import icon %}
{% from "_macros.html" import diff_pill, chip, sb_row %}
{% block title %}Reference — {{ platform.name }}{% endblock %}

{% block storyboard %}
  <div class="sb-eyebrow">Reference</div>
  <div class="sb-title">Authoring Reference</div>
  <div class="sb-goal">The controlled vocabularies used across the case library and activity builder.</div>
  <div class="sb-div"></div>
  {{ sb_row('image', 'Difficulty tiers', reference.difficulty | length) }}
  {{ sb_row('sliders', 'Adaptive tags', reference.adaptive_tags | length) }}
  {{ sb_row('info', 'Question types', reference.question_types | length) }}
  {{ sb_row('layers', 'Case types', reference.case_types | length) }}
{% endblock %}

{% block content %}
<div class="crumbs"><a href="{{ url_for('overview') }}">Overview</a><span class="sep">›</span>Reference</div>

<div class="section-banner">
  <span class="section-kicker">Reference</span>
  <h2>Controlled Vocabularies</h2>
  <span class="sub">Difficulty · tags · question &amp; case types</span>
</div>

<div class="grid-2" style="align-items:start">
  <div style="display:flex; flex-direction:column; gap:12px">
    <div class="card">
      <div class="card-head"><span class="keyline"></span><h3>Difficulty Tiers</h3></div>
      <div class="grid-wrap">
        <table class="deftable">
          <thead><tr><th style="width:90px">Tier</th><th>Definition</th></tr></thead>
          <tbody>
            {% for d in reference.difficulty %}
            <tr><td>{{ diff_pill(d.level) }}</td><td>{{ d.definition }}</td></tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>

    <div class="card">
      <div class="card-head"><span class="keyline"></span><h3>Question Types</h3></div>
      <div class="card-body" style="display:flex; flex-wrap:wrap; gap:8px">
        {% for q in reference.question_types %}{{ chip(q) }}{% endfor %}
      </div>
    </div>

    <div class="card">
      <div class="card-head"><span class="keyline"></span><h3>Case Types</h3></div>
      <div class="card-body" style="display:flex; flex-wrap:wrap; gap:8px">
        {% for t in reference.case_types %}{{ chip(t) }}{% endfor %}
      </div>
    </div>
  </div>

  <div style="display:flex; flex-direction:column; gap:12px">
    <div class="card">
      <div class="card-head"><span class="keyline"></span><h3>Adaptive Tags</h3><div class="actions"><span class="pts">{{ reference.adaptive_tags | length }}</span></div></div>
      <div class="card-body" style="display:flex; flex-wrap:wrap; gap:8px">
        {% for t in reference.adaptive_tags %}{{ chip(t) }}{% endfor %}
      </div>
    </div>

    <div class="card">
      <div class="card-head"><span class="keyline"></span><h3>AI Compatibility</h3></div>
      <div class="card-body" style="display:flex; flex-wrap:wrap; gap:8px">
        {% for a in reference.ai_compatible %}
          {% if a|lower == 'yes' %}{{ chip('yes', 'ai') }}{% elif a|lower == 'future' %}{{ chip('future', 'future') }}{% else %}{{ chip(a) }}{% endif %}
        {% endfor %}
      </div>
      <div class="card-body" style="border-top:1px solid var(--cell-sep)">
        <div class="callout">{{ icon('ai', 18) }}<div class="ct"><b>AI-comparison</b> is enabled in Modules {{ stats.ai_modules | join(', ') }} — students compare their read against a Socratic AI tutor and can refine through dialogue.</div></div>
      </div>
    </div>
  </div>
</div>
{% endblock %}
```

## Phase 3 CSS additions (append to OrbitShell.vue's non-scoped style block)

IMPORTANT rename: the source's `.binary .btn` collides with Bootstrap's global
`.btn` — in both the markup and this CSS it has been renamed to `.bin-btn`.
Use `.bin-btn` in the Vue template for case.html's binary options.

```css
.crumbs{font-size:12px; color:var(--muted); margin:0 0 10px}
.crumbs a{color:var(--action); text-decoration:none}
.crumbs a:hover{text-decoration:underline}
.crumbs .sep{margin:0 6px; color:#B7C0C9}

.sb-chip{display:inline-flex; align-items:center; background:var(--slate-alt); color:var(--rail-value);
  font-size:11px; font-weight:600; padding:2px 8px; border-radius:var(--r-chip)}

.filter-bar{display:flex; gap:10px; flex-wrap:wrap; align-items:center; padding:10px 12px; background:#fff;
  border:1px solid var(--border); border-radius:var(--r-card); box-shadow:var(--shadow-card); margin-bottom:12px}
.filter-bar .fl{font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:.03em; color:var(--muted); margin-right:2px}
.filter-bar label{display:flex; align-items:center; gap:6px; font-size:12px; color:var(--muted); margin-bottom:0}
.filter-bar select{font-family:inherit; font-size:12px; color:var(--ink); background:var(--zebra);
  border:1px solid var(--border); border-radius:var(--r-card); padding:5px 8px; cursor:pointer}
.filter-bar select:focus{outline:2px solid var(--action); outline-offset:-1px}
.filter-bar .count{margin-left:auto; font-size:12px; color:var(--muted)}
.filter-bar .count b{color:var(--ink); font-variant-numeric:tabular-nums}

table.data-grid.tight{min-width:0}
.data-grid .caret{font-size:8px; margin-left:4px; color:#9AA7B4}
.data-grid .caret.active{color:var(--action)}
.data-grid .notes{color:var(--muted); max-width:240px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap}
.data-grid tbody tr.rowlink{cursor:pointer}

.mastery{display:inline-flex; align-items:center; height:18px; padding:0 7px; border-radius:var(--r-pill); font-size:10px; font-weight:700; background:var(--ai-fill); color:var(--ai-text)}
.mastery--improve{background:#EEF7EE; color:#2E6B33}
.chip--future{opacity:.85}

.mod-header{background:var(--card); border:1px solid var(--border); border-radius:var(--r-card); box-shadow:var(--shadow-card); padding:14px 16px; margin-bottom:12px}
.mod-header .top{display:flex; align-items:center; gap:10px; flex-wrap:wrap}
.mod-header .mnum{font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:var(--muted)}
.mod-header h3{font-size:15px; font-weight:600; margin:0; color:var(--ink)}
.goal-edit{display:flex; align-items:center; gap:8px; margin-top:8px; padding:7px 10px; background:var(--zebra); border:1px solid var(--border); border-radius:var(--r-card); font-size:13px; color:var(--ink)}
.mod-note{margin-top:8px; font-size:12px; color:var(--muted)}
.mod-note b{color:var(--ink)}
.mod-kpis{display:flex; gap:20px; flex-wrap:wrap; margin-top:12px; padding-top:12px; border-top:1px solid var(--cell-sep)}
.mod-kpi .k{font-size:20px; font-weight:700; color:var(--ink); font-variant-numeric:tabular-nums}
.mod-kpi .l{font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:.03em; color:var(--muted); margin-top:2px}

.obj-row{display:flex; gap:10px; align-items:flex-start; padding:10px 12px; border-bottom:1px solid var(--cell-sep)}
.obj-row:last-child{border-bottom:0}
.obj-row:hover{background:var(--zebra)}
.obj-num{flex:0 0 20px; font-size:12px; font-weight:700; color:var(--muted); font-variant-numeric:tabular-nums; margin-top:1px}
.obj-body{flex:1 1 auto; min-width:0}
.obj-text{font-size:13px; color:var(--ink); line-height:1.4}
.obj-meta{display:flex; gap:6px; flex-wrap:wrap; margin-top:6px; align-items:center}
.obj-meta .qt{font-size:11px; color:var(--muted)}

.mod-nav{display:flex; justify-content:space-between; align-items:center; gap:10px; margin-top:14px}
.mod-nav a{display:inline-flex; align-items:center; gap:6px; font-size:12px; color:var(--action); text-decoration:none; padding:7px 12px; border:1px solid var(--border); border-radius:var(--r-card); background:#fff}
.mod-nav a:hover{border-color:var(--action)}
.mod-nav .spacer{flex:1}

.activity-head{background:var(--card); border:1px solid var(--border); border-radius:var(--r-card); box-shadow:var(--shadow-card); padding:12px 14px; margin-bottom:12px}
.activity-head .top{display:flex; align-items:baseline; gap:10px; flex-wrap:wrap}
.activity-head h3{font-size:15px; font-weight:600; margin:0; color:var(--ink)}
.id-chips{display:flex; gap:6px; flex-wrap:wrap; margin-top:10px; align-items:center}
.activity-body{display:grid; grid-template-columns:300px 1fr; gap:12px; align-items:start}
@media(max-width:900px){.activity-body{grid-template-columns:1fr}}
.viewer{background:var(--card); border:1px solid var(--border); border-radius:var(--r-card); box-shadow:var(--shadow-card); position:sticky; top:60px; overflow:hidden}
@media(max-width:900px){.viewer{position:static}}
.xray{aspect-ratio:4/3; background:repeating-linear-gradient(135deg,#e9edf1,#e9edf1 10px,#eef2f5 10px,#eef2f5 20px);
  display:flex; flex-direction:column; align-items:center; justify-content:center; gap:6px; color:var(--muted)}
.xray .cap{font-size:11px; color:var(--muted)}
.viewer-foot{padding:8px 10px; border-top:1px solid var(--border); display:flex; justify-content:space-between; align-items:center}
.viewer-foot .tot{font-size:13px; font-weight:600; color:var(--ink)}
.viewer-foot .tot b{color:var(--action); font-variant-numeric:tabular-nums}
.stepper{display:flex; flex-direction:column; gap:10px}
.step{background:var(--card); border:1px solid var(--border); border-radius:var(--r-card); box-shadow:var(--shadow-card); overflow:hidden}
.step-top{display:flex; gap:10px; align-items:flex-start; padding:10px 12px; border-bottom:1px solid var(--cell-sep)}
.step-no{flex:0 0 24px; height:24px; border-radius:50%; background:var(--action); color:#fff; display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:700}
.step-prompt{flex:1 1 auto; font-size:13px; font-weight:600; color:var(--ink); margin-top:2px}
.step-tags{flex:0 0 auto; display:flex; gap:5px; flex-wrap:wrap; justify-content:flex-end; max-width:220px; align-items:center}
.step-body{padding:12px}
.opts{display:flex; flex-direction:column; gap:6px}
.opt{display:flex; align-items:center; gap:8px; padding:7px 10px; border:1px solid var(--border); border-radius:var(--r-card); font-size:13px; color:var(--ink); background:#fff}
.opt .radio{width:14px; height:14px; border-radius:50%; border:1.5px solid #B7C0C9; flex:0 0 14px}
.opt.correct{background:var(--ai-fill); border-color:var(--ai-border)}
.opt.correct .radio{border-color:var(--action); background:radial-gradient(circle,var(--action) 0 4px,#fff 4px 7px,var(--action) 7px)}
.opt.correct .ck{margin-left:auto; color:var(--action); font-size:11px; font-weight:700}
.binary{display:flex; gap:8px}
.binary .bin-btn{flex:1; text-align:center; padding:8px; border:1px solid var(--border); border-radius:var(--r-card); font-size:13px; font-weight:600; color:var(--ink); background:#fff}
.binary .bin-btn.correct{background:var(--ai-fill); border-color:var(--ai-border); color:var(--ai-text)}
.compare{display:grid; grid-template-columns:1fr 1fr; gap:10px}
.compare .pane{border:1px solid var(--border); border-radius:var(--r-card); overflow:hidden}
.compare .plab{font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:.03em; color:var(--muted); padding:6px 8px; background:var(--header-gray); border-bottom:1px solid var(--border)}
.compare .pimg{aspect-ratio:4/3; background:repeating-linear-gradient(135deg,#e9edf1,#e9edf1 8px,#eef2f5 8px,#eef2f5 16px); display:flex; align-items:center; justify-content:center; color:#9AA7B4}
.step-foot{margin-top:10px; padding-top:10px; border-top:1px solid var(--cell-sep); display:flex; align-items:center; gap:8px}
.step-foot .fb{font-size:12px; color:var(--muted); font-style:italic}
.step-foot .fb b{color:var(--ink); font-style:normal; font-weight:600}
.correct-line{display:flex; align-items:center; gap:6px; margin-bottom:10px; font-size:12px; color:var(--muted)}
.correct-line b{color:var(--ink); font-weight:600}

.deftable{border-collapse:collapse; width:100%}
.deftable th{background:var(--header-gray); text-align:left; font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:.03em; color:var(--muted); padding:7px 10px; border-bottom:2px solid var(--border)}
.deftable td{padding:8px 10px; font-size:13px; border-bottom:1px solid var(--cell-sep); vertical-align:top}
.deftable tr:nth-child(even) td{background:var(--zebra)}

.workspace .empty{padding:34px 20px; text-align:center; color:var(--muted)}
.workspace .empty .et{font-size:13px; font-weight:600; color:var(--ink)}
.workspace .empty .es{font-size:12px; color:var(--muted); margin-top:4px}
```

## Hard constraints

- Plain JavaScript, `<script setup>`, 2-space indent, single quotes. No
  TypeScript, no new npm packages, no lockfile changes, no icon libraries.
- Do not touch: env SCSS files, main.js, vite.config.js, package.json,
  anything under src/app/, OrbitNavbar.vue, App.vue, publicRoutes, or any
  existing demo/page component.
- The word "Epic" must not appear anywhere.
- All existing routes and demos must keep working. Run `npm run build:dev`
  from src/frontend and confirm it passes.
- Then list every file created/changed with a one-line summary and stop.
  Do not commit or push.
