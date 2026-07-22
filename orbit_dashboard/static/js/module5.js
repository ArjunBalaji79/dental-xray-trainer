/* ORBIT — Module 5 interactive trainer (Radiographic Interpretation & AI Comparison).
   Per case: mark the area -> identify tooth/surface -> name the finding ->
   decide vs the AI interpretation -> faculty review. Two cases feature a WRONG AI
   read, so blindly accepting it costs you the point (objectives 5, 6, 8). */
(function () {
  "use strict";

  var DATA = JSON.parse(document.getElementById("m5-data").textContent);
  var CASES = DATA.cases, OBJ = DATA.module.objectives, TOTAL_PTS = DATA.total_points;
  var KIND_LABEL = { area: "Mark the area", tooth: "Identify tooth & surface",
    select: "Primary finding", ai: "Compare with AI", faculty: "Faculty review" };

  var app = document.getElementById("p5-app");
  var progress = document.getElementById("p5-progress");
  var state, records;

  function reset() {
    state = { idx: 0, sub: 0 };
    records = CASES.map(function (c) { return c.steps.map(function () { return null; }); });
  }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function icon(p, sw, size) { return '<svg class="glyph" width="' + (size || 16) + '" height="' + (size || 16) +
    '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="' + (sw || 1.6) +
    '" stroke-linecap="round" stroke-linejoin="round">' + p + "</svg>"; }
  var I_CHECK = icon('<path d="M20 6 9 17l-5-5"/>', 2);
  var I_X = icon('<path d="M18 6 6 18M6 6l12 12"/>', 2);
  var I_ARROW = icon('<path d="M5 12h14M12 5l7 7-7 7"/>');
  var I_AI = icon('<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M8 12h8M8 8h8M8 16h5"/>');
  function norm(s) { return " " + String(s || "").toLowerCase().trim() + " "; }

  function earned() {
    var p = 0;
    CASES.forEach(function (c, ci) { c.steps.forEach(function (s, si) {
      var r = records[ci][si]; if (r && r.ok) p += s.points; }); });
    return p;
  }
  function stat(kind) {
    var ok = 0, of = 0;
    CASES.forEach(function (c, ci) { c.steps.forEach(function (s, si) {
      if (s.kind === kind) { of++; if (records[ci][si] && records[ci][si].ok) ok++; } }); });
    return { ok: ok, of: of };
  }
  function aiTrapStat() {
    var ok = 0, of = 0;
    CASES.forEach(function (c, ci) { c.steps.forEach(function (s, si) {
      if (s.kind === "ai" && s.ai_correct === false) { of++; if (records[ci][si] && records[ci][si].ok) ok++; } }); });
    return { ok: ok, of: of };
  }

  function updateChrome() {
    var total = 0, done = 0;
    CASES.forEach(function (c, ci) { total += c.steps.length;
      if (ci < state.idx) done += c.steps.length; else if (ci === state.idx) done += state.sub; });
    var b = document.getElementById("p5-bar"); if (b) b.style.width = Math.round(done / total * 100) + "%";
    var l = document.getElementById("p5-lab"); if (l) l.textContent = "Case " + (state.idx + 1) + " of " + CASES.length;
    var s = document.getElementById("p5-score"); if (s) s.textContent = earned() + " pts";
    var sb = document.getElementById("sb-score"); if (sb) sb.textContent = earned() + " / " + TOTAL_PTS + " pts";
    var a = stat("ai");
    var sa = document.getElementById("sb-acc"); if (sa) sa.textContent = a.of ? (a.ok + " / " + a.of + " sound") : "—";
    document.querySelectorAll("#sb-caselist [data-caseidx]").forEach(function (n) {
      n.className = (+n.getAttribute("data-caseidx") === state.idx) ? "sb-list-item" : "sb-plain-item"; });
  }

  function viewer(c, clickable, marker) {
    var dot = marker ? '<div class="m5-marker" style="left:' + marker.x + '%; top:' + marker.y + '%"></div>' : "";
    return '<div class="p4-view"><div class="p1-film' + (clickable ? " m5-clickable" : "") + '" id="film">' +
      '<div class="p1-corner tl"></div><div class="p1-corner tr"></div><div class="p1-corner bl"></div><div class="p1-corner br"></div>' +
      icon('<rect x="4" y="5" width="16" height="14" rx="2"/><path d="M9 5v14M13 5v14M17 5v14"/>', 1.1, 42) +
      '<div class="p1-mod">' + esc(c.id) + " · " + esc(c.name) + "</div>" + dot +
      (clickable ? '<div class="m5-hint">Click to place your marker</div>' : "") + "</div>" +
      '<div class="vcap"><div class="roinote">Representative film · illustrative (reference image pending)</div>' +
      '<div class="finding">Evaluate the radiograph and work through the steps — the diagnosis is revealed as you go.</div></div></div>';
  }

  function choices(options, isOk, chosen, locked) {
    return options.map(function (opt) {
      var ok = isOk(opt), cls = "choice";
      if (locked) { if (ok) cls += " correct"; else if (opt === chosen) cls += " wrong"; else cls += " muted"; }
      else if (opt === chosen) cls += " selected";
      var mark = (locked && ok) ? I_CHECK : (locked && opt === chosen) ? I_X : "";
      var tag = locked ? (ok ? '<span class="tag">Correct</span>' : (opt === chosen ? '<span class="tag">Your pick</span>' : "")) : "";
      return '<button class="' + cls + '" data-opt="' + esc(opt) + '"' + (locked ? " disabled" : "") + '>' +
        '<span class="mark">' + mark + '</span><span class="txt">' + esc(opt) + "</span>" + tag + "</button>";
    }).join("");
  }
  function fb(ok, body, lead) {
    return '<div class="feedback ' + (ok ? "ok" : "no") + '"><div class="lead">' + (ok ? I_CHECK : I_X) +
      (lead || (ok ? "Correct" : "Not quite")) + "</div><div>" + body + "</div></div>";
  }

  function renderIntro() {
    progress.style.display = "none";
    app.innerHTML = '<div class="p4-hero"><h1>Module 5 — ' + esc(DATA.module.title) + "</h1>" +
      '<div class="lead">' + esc(DATA.module.goal) + "</div>" +
      '<div class="callout" style="margin-top:14px">' + I_AI + '<div class="ct"><b>The AI is not always right.</b> ' +
      'In two of these cases the AI interpretation is wrong — accepting it costs you the point. Use the radiographic evidence to decide.</div></div>' +
      '<div class="obj-grid">' + OBJ.map(function (o) {
        return '<div class="obj-card"><div class="n">' + o.n + '</div><div><div class="t">' + esc(o.text) + "</div>" +
          (o.target ? '<span class="mastery' + (o.kind === "improvement" ? " mastery--improve" : "") + '">' + o.target + "</span>" : "") +
          "</div></div>"; }).join("") + "</div>" +
      '<div class="q-actions" style="margin-top:16px"><button class="btn-primary" id="p5-begin">' +
      icon('<path d="M6 4l14 8-14 8z" fill="currentColor" stroke="none"/>') + " Begin practice · " + CASES.length + " cases</button>" +
      '<span class="pts">Mark area → tooth &amp; surface → finding → AI decision → faculty review. ' + TOTAL_PTS + " points.</span></div></div>";
    document.getElementById("p5-begin").addEventListener("click", function () {
      state = { idx: 0, sub: 0 }; progress.style.display = "flex"; render(); });
    updateChrome();
  }

  function render() {
    var c = CASES[state.idx], s = c.steps[state.sub], rec = records[state.idx][state.sub];
    var locked = rec != null && rec.ok !== undefined;   // tooth step may hold a partial pick
    var auto = (s.kind === "faculty");
    var complete = locked || auto;
    if (auto && !locked) records[state.idx][state.sub] = { ok: true };

    var q = '<div class="p4-q"><div class="p4-qhead"><span class="keyline"></span>' +
      '<span class="qstep">Step ' + s.n + " · " + (KIND_LABEL[s.kind] || s.kind) + "</span>" +
      '<span class="objtag"><span class="mastery">Obj ' + esc(s.objective) + "</span></span></div>" +
      '<div class="p4-qbody"><div class="p4-prompt">' + esc(s.prompt) + "</div>";

    if (s.kind === "area") {
      if (!locked) q += '<div class="pts">Click the radiograph to place your marker.</div>';
      else q += fb(true, "<b>Expected region:</b> " + esc(s.expected) + "<br>" + esc(s.feedback), "Marker placed");
    } else if (s.kind === "tooth") {
      var t = rec || {};
      q += '<div class="p4-sub">Tooth</div><div class="choices--two" style="margin-bottom:10px">' +
        choices(s.tooth_options, function (o) { return o === s.tooth; }, t.tooth, locked) + "</div>";
      if (s.needs_surface) {
        q += '<div class="p4-sub">Surface / region</div><div class="choices--two">' +
          choices(s.surface_options, function (o) { return o === s.surface; }, t.surface, locked) + "</div>";
      }
      if (locked) q += fb(rec.ok, esc(s.feedback));
    } else if (s.kind === "ai") {
      q += '<div class="ai-panel">' + I_AI + '<div><div class="ai-lab">AI interpretation</div><div class="ai-txt">' +
        esc(s.ai_interpretation || s.prompt) + "</div></div></div>" +
        choices(s.options, function (o) { return (s.correct_options || []).indexOf(o) !== -1; }, rec && rec.chosen, locked);
      if (locked) {
        q += fb(rec.ok, (s.ai_correct
          ? "The AI read matches the radiographic evidence here, so keeping or accepting it both land on the correct diagnosis. "
          : "<b>The AI was wrong on this case.</b> The evidence does not support the AI's read — keeping your own correct interpretation is the right call. ") +
          esc(s.feedback), s.ai_correct ? "AI was correct" : "AI was incorrect");
      }
    } else if (s.kind === "faculty") {
      var e = s.expert || {};
      var bits = "";
      if (e.correct) bits += "<div><b>Correct interpretation:</b> " + esc(e.correct) + "</div>";
      if (e.why) bits += "<div style='margin-top:6px'><b>Why:</b> " + esc(e.why) + "</div>";
      if (e.pitfall) bits += "<div style='margin-top:6px'><b>Common pitfall:</b> " + esc(e.pitfall) + "</div>";
      if (e.teaching) bits += "<div style='margin-top:6px'><b>Teaching points:</b> " + esc(e.teaching) + "</div>";
      if (e.pearls) bits += "<div style='margin-top:6px'><b>Clinical pearl:</b> " + esc(e.pearls) + "</div>";
      if (!bits) bits = "<div>" + esc(s.feedback) + "</div>";
      q += '<div class="feedback ok"><div class="lead">' + I_CHECK + "Faculty review</div>" + bits + "</div>";
    } else {
      if (locked) q += '<div class="correct-line">' + I_CHECK.replace('stroke="currentColor"', 'stroke="var(--action)"') +
        "<span>Correct answer · <b>" + esc(s.expected) + "</b></span></div>";
      q += choices(s.options, function (o) { return norm(s.expected).indexOf(norm(o)) !== -1; }, rec && rec.chosen, locked);
      if (locked) q += fb(rec.ok, esc(s.feedback));
    }

    if (complete) {
      var last = state.idx === CASES.length - 1 && state.sub === c.steps.length - 1;
      var lastInCase = state.sub === c.steps.length - 1;
      q += '<div class="q-actions"><span class="spacer"></span><button class="btn-primary" id="next">' +
        (last ? "See results " + I_ARROW : lastInCase ? "Next case " + I_ARROW : "Continue " + I_ARROW) + "</button></div>";
    }
    q += "</div></div>";

    app.innerHTML = '<div class="p4-body">' + viewer(c, s.kind === "area" && !locked, rec && rec.marker) + '<div id="qcol">' + q + "</div></div>";
    wire();
    updateChrome();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function wire() {
    var c = CASES[state.idx], s = c.steps[state.sub], rec = records[state.idx][state.sub];
    var film = document.getElementById("film");
    if (film && s.kind === "area" && !rec) {
      film.addEventListener("click", function (ev) {
        var r = film.getBoundingClientRect();
        records[state.idx][state.sub] = { ok: true,
          marker: { x: ((ev.clientX - r.left) / r.width * 100).toFixed(1),
                    y: ((ev.clientY - r.top) / r.height * 100).toFixed(1) } };
        render();
      });
    }
    document.querySelectorAll(".choice:not([disabled])").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var opt = btn.getAttribute("data-opt");
        if (s.kind === "tooth") {
          var cur = records[state.idx][state.sub] || {};
          var partial = { tooth: cur.tooth, surface: cur.surface };
          if (s.tooth_options.indexOf(opt) !== -1) partial.tooth = opt; else partial.surface = opt;
          if (partial.tooth && (!s.needs_surface || partial.surface)) {
            partial.ok = (partial.tooth === s.tooth) && (!s.needs_surface || partial.surface === s.surface);
          }
          records[state.idx][state.sub] = partial;   // keep partial picks visible
          render();
          return;
        }
        var ok = (s.kind === "ai")
          ? (s.correct_options || []).indexOf(opt) !== -1
          : norm(s.expected).indexOf(norm(opt)) !== -1;
        records[state.idx][state.sub] = { chosen: opt, ok: ok };
        render();
      });
    });
    var n = document.getElementById("next"); if (n) n.addEventListener("click", advance);
  }

  function advance() {
    var c = CASES[state.idx];
    if (state.sub < c.steps.length - 1) { state.sub += 1; render(); }
    else if (state.idx < CASES.length - 1) { state.idx += 1; state.sub = 0; render(); }
    else renderSummary();
  }

  function renderSummary() {
    progress.style.display = "none";
    var area = stat("area"), tooth = stat("tooth"), find = stat("select"), ai = stat("ai"), fac = stat("faculty");
    var trap = aiTrapStat(), score = earned();
    var objRes = {
      1: { hit: find.ok, of: find.of, note: "Primary radiographic findings identified" },
      2: { hit: tooth.ok, of: tooth.of, note: "Correct tooth and surface selected" },
      3: { hit: area.ok, of: area.of, note: "Evidence regions marked on the radiograph" },
      4: { hit: find.ok, of: find.of, note: "True pathology told apart from anatomy / artifact" },
      5: { hit: ai.ok, of: ai.of, note: "Sound judgements of the AI interpretation" },
      6: { hit: ai.ok, of: ai.of, note: "Accepted, refined or challenged the AI appropriately" },
      7: { hit: ai.ok, of: ai.of, note: "Diagnostic accuracy held up through AI dialogue" },
      8: { hit: trap.ok, of: trap.of, note: "Resisted the " + trap.of + " incorrect AI read(s)" },
      9: { hit: fac.ok, of: fac.of, note: "Faculty annotations reviewed" }
    };
    function tile(n, cap, note) { return '<div class="kpi-tile"><div class="kpi-num tabular">' + n +
      '</div><div class="kpi-cap">' + cap + '</div><div class="kpi-note">' + note + "</div></div>"; }
    var rows = OBJ.map(function (o) {
      var r = objRes[o.n] || { hit: 0, of: 0, note: "" };
      var hit = r.of > 0 && r.hit >= r.of;
      return '<div class="sum-obj"><div class="ic ' + (hit ? "hit" : "miss") + '">' + (hit ? "✓" : "!") + "</div>" +
        '<div><div class="st">' + esc(o.text) + ' <b class="tabular">' + r.hit + " / " + r.of + "</b></div>" +
        '<div class="sd">' + esc(r.note) + "</div></div></div>"; }).join("");
    app.innerHTML =
      '<div class="section-banner" style="margin-top:4px"><span class="section-kicker">Results</span>' +
      "<h2>Module 5 · Session Summary</h2><span class=\"sub\">" + CASES.length + " cases completed</span></div>" +
      '<div class="sum-tiles">' + tile(score + " / " + TOTAL_PTS, "Score", "2 pts per graded step") +
        tile(find.ok + " / " + find.of, "Findings", "Primary diagnosis correct") +
        tile(ai.ok + " / " + ai.of, "AI decisions", "Sound accept / keep calls") +
        tile(trap.ok + " / " + trap.of, "AI traps resisted", "Wrong AI reads not adopted") + "</div>" +
      '<div class="grid-2"><div class="card"><div class="card-head"><span class="keyline"></span><h3>Objective coverage</h3></div><div>' + rows + "</div></div>" +
      '<div style="display:flex;flex-direction:column;gap:12px">' +
        '<div class="callout">' + I_AI + '<div class="ct"><b>AI reliance.</b> You resisted <b>' + trap.ok + " of " + trap.of +
        "</b> deliberately incorrect AI interpretations — the core skill of Module 5: use the AI, but verify it against the radiographic evidence.</div></div>" +
        '<div class="card"><div class="card-body" style="display:flex;gap:8px;align-items:center">' +
        '<button class="btn-primary" id="restart">' + icon('<path d="M3 2v6h6"/><path d="M3 8a9 9 0 1 0 3-6.7L3 8"/>') +
        ' Restart Module 5</button><a class="btn-ghost" href="/module/5">Back to Module 5</a></div></div></div></div>';
    document.getElementById("restart").addEventListener("click", function () { reset(); renderIntro(); });
    updateChrome();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  reset();
  renderIntro();
})();
