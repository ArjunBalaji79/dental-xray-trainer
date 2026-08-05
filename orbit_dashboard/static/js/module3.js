/* ORBIT — Module 3 interactive trainer (Tooth Identification & Localization).
   Per case: arch -> side -> Universal-number ID -> distinguishing feature ->
   adjacent tooth or anomaly. Pure MCQ; scored; mapped to the 6 objectives. */
(function () {
  "use strict";

  var DATA = JSON.parse(document.getElementById("m3-data").textContent);
  var CASES = DATA.cases, OBJ = DATA.module.objectives, TOTAL_PTS = DATA.total_points;
  var LABEL = { arch: "Arch", side: "Side", tooth: "Identify the tooth",
    feature: "Distinguishing feature", adjacent: "Adjacent tooth", anomaly: "Classify the tooth" };

  var app = document.getElementById("p3-app");
  var progress = document.getElementById("p3-progress");
  var IMGBASE = "/static/img/";
  var state, records;

  function reset() { state = { idx: 0, sub: 0 };
    records = CASES.map(function (c) { return c.steps.map(function () { return null; }); }); }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function icon(p, sw, size) { return '<svg class="glyph" width="' + (size || 16) + '" height="' + (size || 16) +
    '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="' + (sw || 1.6) +
    '" stroke-linecap="round" stroke-linejoin="round">' + p + "</svg>"; }
  var I_CHECK = icon('<path d="M20 6 9 17l-5-5"/>', 2), I_X = icon('<path d="M18 6 6 18M6 6l12 12"/>', 2);
  var I_ARROW = icon('<path d="M5 12h14M12 5l7 7-7 7"/>');
  var I_TOOTH = '<rect x="4" y="5" width="16" height="14" rx="2"/><path d="M9 5v14M13 5v14M17 5v14"/>';
  function norm(s) { return " " + String(s || "").toLowerCase().trim() + " "; }
  function ok_(opt, exp) { return norm(exp).indexOf(norm(opt)) !== -1 && String(opt).trim() !== ""; }

  function earned() { var p = 0; CASES.forEach(function (c, ci) { c.steps.forEach(function (s, si) {
    var r = records[ci][si]; if (r && r.ok) p += s.points; }); }); return p; }
  function keyStat(k) { var ok = 0, of = 0; CASES.forEach(function (c, ci) { c.steps.forEach(function (s, si) {
    if (s.key === k) { of++; if (records[ci][si] && records[ci][si].ok) ok++; } }); }); return { ok: ok, of: of }; }

  function updateChrome() {
    var total = 0, done = 0;
    CASES.forEach(function (c, ci) { total += c.steps.length;
      if (ci < state.idx) done += c.steps.length; else if (ci === state.idx) done += state.sub; });
    var b = document.getElementById("p3-bar"); if (b) b.style.width = Math.round(done / total * 100) + "%";
    var l = document.getElementById("p3-lab"); if (l) l.textContent = "Case " + (state.idx + 1) + " of " + CASES.length;
    var s = document.getElementById("p3-score"); if (s) s.textContent = earned() + " pts";
    var sb = document.getElementById("sb-score"); if (sb) sb.textContent = earned() + " / " + TOTAL_PTS + " pts";
    var t = keyStat("tooth"); var sa = document.getElementById("sb-acc");
    if (sa) sa.textContent = t.of ? (t.ok + " / " + t.of + " correct") : "—";
    document.querySelectorAll("#sb-caselist [data-caseidx]").forEach(function (n) {
      n.className = (+n.getAttribute("data-caseidx") === state.idx) ? "sb-list-item" : "sb-plain-item"; });
  }

  function filmHTML(c) {
    var roi = c.roi ? '<div class="roi" style="left:' + c.roi.x + '%; top:' + c.roi.y + '%; width:' + (c.roi.r * 2) + '%; aspect-ratio:1"></div>' : '';
    var inner = c.image
      ? '<div class="imgwrap"><img src="' + IMGBASE + esc(c.image) + '" alt="periapical radiograph">' + roi + '</div>'
      : '<div class="p1-film"><div class="p1-corner tl"></div><div class="p1-corner tr"></div><div class="p1-corner bl"></div><div class="p1-corner br"></div><div class="p1-mod">' + esc(c.id) + '</div></div>';
    var cap = c.image ? 'DenPAR intra-oral periapical · highlighted region illustrative'
                      : 'Representative film · illustrative (reference image pending)';
    return '<div class="p4-view">' + inner +
      '<div class="vcap"><div class="roinote">' + cap + '</div>' +
      '<div class="finding">' + esc(c.finding) + '</div></div></div>';
  }
  function choicesHTML(options, expected, chosen, locked, two) {
    return '<div class="choices' + (two ? " choices--two" : "") + '">' + options.map(function (opt) {
      var ok = ok_(opt, expected), cls = "choice";
      if (locked) { if (ok) cls += " correct"; else if (opt === chosen) cls += " wrong"; else cls += " muted"; }
      else if (opt === chosen) cls += " selected";
      var mark = (locked && ok) ? I_CHECK : (locked && opt === chosen) ? I_X : "";
      var tag = locked ? (ok ? '<span class="tag">Correct</span>' : (opt === chosen ? '<span class="tag">Your pick</span>' : "")) : "";
      return '<button class="' + cls + '" data-opt="' + esc(opt) + '"' + (locked ? " disabled" : "") + '>' +
        '<span class="mark">' + mark + '</span><span class="txt">' + esc(opt) + "</span>" + tag + "</button>";
    }).join("") + "</div>";
  }
  function fb(ok, body) { return '<div class="feedback ' + (ok ? "ok" : "no") + '"><div class="lead">' +
    (ok ? I_CHECK : I_X) + (ok ? "Correct" : "Not quite") + "</div><div>" + esc(body) + "</div></div>"; }

  function renderIntro() {
    progress.style.display = "none";
    app.innerHTML = '<div class="p4-hero"><h1>Module 3 — ' + esc(DATA.module.title) + "</h1>" +
      '<div class="lead">' + esc(DATA.module.goal) + "</div><div class=\"obj-grid\">" +
      OBJ.map(function (o) { return '<div class="obj-card"><div class="n">' + o.n + '</div><div><div class="t">' +
        esc(o.text) + "</div>" + (o.target ? '<span class="mastery">' + o.target + "</span>" : "") + "</div></div>"; }).join("") +
      '</div><div class="q-actions" style="margin-top:16px"><button class="btn-primary" id="p3-begin">' +
      icon('<path d="M6 4l14 8-14 8z" fill="currentColor" stroke="none"/>') + " Begin practice · " + CASES.length + " cases</button>" +
      '<span class="pts">Arch → side → tooth number → feature → adjacency / anomaly. ' + TOTAL_PTS + " points.</span></div></div>";
    document.getElementById("p3-begin").addEventListener("click", function () {
      state = { idx: 0, sub: 0 }; progress.style.display = "flex"; renderStep(); });
    updateChrome();
  }

  function renderStep() {
    var c = CASES[state.idx], s = c.steps[state.sub], rec = records[state.idx][state.sub];
    var locked = rec != null, two = s.options.length === 2;
    var q = '<div class="p4-q"><div class="p4-qhead"><span class="keyline"></span>' +
      '<span class="qstep">Step ' + s.n + " · " + (LABEL[s.key] || s.key) + "</span>" +
      '<span class="objtag"><span class="mastery">Obj ' + s.objective + "</span></span></div>" +
      '<div class="p4-qbody"><div class="p4-prompt">' + esc(s.prompt) + "</div>";
    if (locked) q += '<div class="correct-line">' + I_CHECK.replace('stroke="currentColor"', 'stroke="var(--action)"') +
      "<span>Correct answer · <b>" + esc(s.expected) + "</b></span></div>";
    q += choicesHTML(s.options, s.expected, rec && rec.chosen, locked, two);
    if (locked) q += fb(rec.ok, s.feedback);
    if (locked) {
      var last = state.idx === CASES.length - 1 && state.sub === c.steps.length - 1;
      var lastInCase = state.sub === c.steps.length - 1;
      q += '<div class="q-actions"><span class="spacer"></span><button class="btn-primary" id="next">' +
        (last ? "See results " + I_ARROW : lastInCase ? "Next case " + I_ARROW : "Continue " + I_ARROW) + "</button></div>";
    }
    q += "</div></div>";
    app.innerHTML = '<div class="p4-body">' + filmHTML(c) + '<div id="qcol">' + q + "</div></div>";
    document.querySelectorAll(".choice:not([disabled])").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var opt = btn.getAttribute("data-opt");
        records[state.idx][state.sub] = { chosen: opt, ok: ok_(opt, s.expected) };
        renderStep();
      });
    });
    var n = document.getElementById("next"); if (n) n.addEventListener("click", advance);
    updateChrome(); window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function advance() {
    var c = CASES[state.idx];
    if (state.sub < c.steps.length - 1) { state.sub += 1; renderStep(); }
    else if (state.idx < CASES.length - 1) { state.idx += 1; state.sub = 0; renderStep(); }
    else renderSummary();
  }

  function renderSummary() {
    progress.style.display = "none";
    var arch = keyStat("arch"), side = keyStat("side"), tooth = keyStat("tooth"),
        feat = keyStat("feature"), adj = keyStat("adjacent"), anom = keyStat("anomaly");
    var objRes = {
      1: { r: tooth, note: "Teeth identified by Universal number" },
      2: { r: side, note: "Right / left side correctly localized" },
      3: { r: arch, note: "Maxillary / mandibular correctly localized" },
      4: { r: feat, note: "Similar teeth distinguished by morphology" },
      5: { r: adj, note: "Adjacent teeth & relationships identified" },
      6: { r: anom, note: "Missing / restored / impacted teeth classified" }
    };
    function tile(n, cap, note) { return '<div class="kpi-tile"><div class="kpi-num tabular">' + n +
      '</div><div class="kpi-cap">' + cap + '</div><div class="kpi-note">' + note + "</div></div>"; }
    var rows = OBJ.map(function (o) { var res = objRes[o.n] || { r: { ok: 0, of: 0 }, note: "" };
      var hit = res.r.of > 0 && res.r.ok >= res.r.of;
      return '<div class="sum-obj"><div class="ic ' + (hit ? "hit" : "miss") + '">' + (hit ? "✓" : "!") + "</div>" +
        '<div><div class="st">' + esc(o.text) + ' <b class="tabular">' + res.r.ok + " / " + res.r.of + "</b></div>" +
        '<div class="sd">' + esc(res.note) + "</div></div></div>"; }).join("");
    app.innerHTML = '<div class="section-banner" style="margin-top:4px"><span class="section-kicker">Results</span>' +
      "<h2>Module 3 · Session Summary</h2><span class=\"sub\">" + CASES.length + " cases completed</span></div>" +
      '<div class="sum-tiles">' + tile(earned() + " / " + TOTAL_PTS, "Score", "arch/side 1 · rest 2 pts") +
        tile(tooth.ok + " / " + tooth.of, "Teeth IDed", "Universal number correct") +
        tile(arch.ok + " / " + arch.of, "Arch", "Maxillary / mandibular") +
        tile(side.ok + " / " + side.of, "Side", "Right / left") + "</div>" +
      '<div class="grid-2"><div class="card"><div class="card-head"><span class="keyline"></span><h3>Objective coverage</h3></div><div>' + rows + "</div></div>" +
      '<div style="display:flex;flex-direction:column;gap:12px"><div class="callout">' +
      icon('<path d="m12 3 9 5-9 5-9-5 9-5z"/><path d="m3 13 9 5 9-5"/>') +
      '<div class="ct"><b>Localization workflow.</b> Arch → side → tooth number, then confirm with root/crown morphology and neighbouring teeth — the systematic read for every radiograph.</div></div>' +
      '<div class="card"><div class="card-body" style="display:flex;gap:8px;align-items:center"><button class="btn-primary" id="restart">' +
      icon('<path d="M3 2v6h6"/><path d="M3 8a9 9 0 1 0 3-6.7L3 8"/>') + ' Restart Module 3</button>' +
      '<a class="btn-ghost" href="/module/3">Back to Module 3</a></div></div></div></div>';
    document.getElementById("restart").addEventListener("click", function () { reset(); renderIntro(); });
    updateChrome(); window.scrollTo({ top: 0, behavior: "smooth" });
  }

  reset();
  renderIntro();
})();
