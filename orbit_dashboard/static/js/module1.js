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
    return '<div class="p4-view">' +
      '<div class="p1-film"><div class="p1-corner tl"></div><div class="p1-corner tr"></div><div class="p1-corner bl"></div><div class="p1-corner br"></div>' +
        icon('<rect x="4" y="5" width="16" height="14" rx="2"/><path d="M9 5v14M13 5v14M17 5v14"/>', 1.1).replace('width="16" height="16"', 'width="42" height="42"') +
        '<div class="p1-mod">' + esc(c.modality) + " · " + esc(c.id) + "</div></div>" +
      '<div class="vcap"><div class="roinote">Representative film · illustrative (reference image pending)</div>' +
      '<div class="finding">' + esc(c.finding) + "</div></div></div>";
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
