/* ORBIT — Module 5 interactive trainer (Radiographic Interpretation & AI Comparison).
   Per case: draw a box around the area you'd evaluate first (graded by the AI Companion,
   which sees the radiograph) -> identify tooth/surface -> name the finding -> decide vs a
   separate AI interpretation (deliberately wrong in two cases) -> faculty review.
   The AI Companion also offers the Learning Framework's 3-level coaching ladder and a
   chat that is grounded in the image and the student's marked region. */
(function () {
  "use strict";

  var DATA = JSON.parse(document.getElementById("m5-data").textContent);
  var CASES = DATA.cases, OBJ = DATA.module.objectives, TOTAL_PTS = DATA.total_points;
  var KIND_LABEL = { area: "Mark the area", tooth: "Identify tooth & surface",
    select: "Primary finding", ai: "Compare with AI", faculty: "Faculty review" };
  var HINT_LABEL = { 1: "Direct attention", 2: "Guide reasoning", 3: "Reinforce concept" };

  var app = document.getElementById("p5-app");
  var progress = document.getElementById("p5-progress");
  var IMGBASE = "/static/img/";

  var preloaded = {};
  function preloadNext(idx) {
    var n = CASES[idx + 1];
    if (!n || !n.image || preloaded[n.image]) return;
    preloaded[n.image] = true;
    (new Image()).src = IMGBASE + n.image;
  }

  var state, records, ui;
  function reset() {
    state = { idx: 0, sub: 0 };
    records = CASES.map(function (c) { return c.steps.map(function () { return null; }); });
    ui = CASES.map(function () { return { box: null, evaluating: false, coachOpen: false, hints: [],
      hintBusy: false, redraws: 0, compOpen: false, chat: [], compBusy: false, compSource: "" }; });
  }
  function U() { return ui[state.idx]; }

  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function icon(p, sw, size) { return '<svg class="glyph" width="' + (size || 16) + '" height="' + (size || 16) +
    '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="' + (sw || 1.6) +
    '" stroke-linecap="round" stroke-linejoin="round">' + p + "</svg>"; }
  var I_CHECK = icon('<path d="M20 6 9 17l-5-5"/>', 2);
  var I_X = icon('<path d="M18 6 6 18M6 6l12 12"/>', 2);
  var I_ARROW = icon('<path d="M5 12h14M12 5l7 7-7 7"/>');
  var I_AI = icon('<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M8 12h8M8 8h8M8 16h5"/>');
  var I_BOX = icon('<rect x="4" y="4" width="16" height="16" rx="2" stroke-dasharray="3 2"/><path d="M9 12h6M12 9v6"/>');
  function norm(s) { return " " + String(s || "").toLowerCase().trim() + " "; }
  function postJSON(url, body) {
    return fetch(url, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body) }).then(function (r) { return r.json(); });
  }

  // ---- scoring / stats -------------------------------------------------------
  function earned() {
    var p = 0;
    CASES.forEach(function (c, ci) { c.steps.forEach(function (s, si) {
      var r = records[ci][si];
      if (r && r.ok) p += (typeof r.pts === "number" ? r.pts : s.points); }); });
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
  function areaStats() {
    var o = { hit: 0, partial: 0, miss: 0, placed: 0, of: 0 };
    CASES.forEach(function (c, ci) { c.steps.forEach(function (s, si) {
      if (s.kind !== "area") return; o.of++;
      var r = records[ci][si]; if (r && o[r.verdict] != null) o[r.verdict]++; }); });
    return o;
  }
  function hintsUsed() { return ui.reduce(function (n, u) { return n + u.hints.length; }, 0); }

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

  // ---- viewer (real radiograph + selection overlay) ----------------------------
  // Spotlight: four dim bands around the box (no clip-path — paints reliably everywhere).
  function maskHTML(b) {
    function band(l, t, w, h) { return '<div class="sel-mask" style="left:' + l + '%;top:' + t + '%;width:' + w + '%;height:' + h + '%"></div>'; }
    var x2 = r1(b.x + b.w), y2 = r1(b.y + b.h);
    return band(0, 0, 100, b.y) + band(0, y2, 100, r1(100 - y2)) +
           band(0, b.y, b.x, b.h) + band(x2, b.y, r1(100 - x2), b.h);
  }
  function viewer(c, selectable, box) {
    var selHTML = (box ? maskHTML(box) : "") + (box
      ? '<div class="sel" id="sel" style="left:' + box.x + '%;top:' + box.y + '%;width:' + box.w + '%;height:' + box.h + '%"></div>'
      : '<div class="sel" id="sel" style="display:none"></div>');
    var layer = selectable ? '<div class="sel-layer" id="sel-layer"></div>' : "";
    var hint = (selectable && !box) ? '<div class="m5-hint">Drag to draw a box around the area to evaluate</div>' : "";
    var inner = c.image
      ? '<div class="imgwrap" id="film"><img src="' + IMGBASE + esc(c.image) + '" alt="periapical radiograph" draggable="false">' + selHTML + layer + hint + "</div>"
      : '<div class="p1-film" id="film"><div class="p1-corner tl"></div><div class="p1-corner tr"></div><div class="p1-corner bl"></div><div class="p1-corner br"></div><div class="p1-mod">' + esc(c.id) + "</div>" + selHTML + layer + hint + "</div>";
    var cap = box ? "DenPAR intra-oral periapical · your marked region" : "DenPAR intra-oral periapical";
    return '<div class="p4-view">' + inner +
      '<div class="vcap"><div class="roinote">' + cap + "</div>" +
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

  // ---- intro --------------------------------------------------------------------
  function renderIntro() {
    progress.style.display = "none";
    app.innerHTML = '<div class="p4-hero"><h1>Module 5 — ' + esc(DATA.module.title) + "</h1>" +
      '<div class="lead">' + esc(DATA.module.goal) + "</div>" +
      '<div class="callout" style="margin-top:14px">' + I_AI + '<div class="ct"><b>Your AI Companion sees the radiograph.</b> ' +
      "Draw a box around the area you'd evaluate first and it grades your selection from the image; ask for up to three coaching hints if you're unsure, " +
      "or chat with it about what you see. <b>The separate AI interpretation you'll compare against is wrong in two cases</b> — accepting it costs the point.</div></div>" +
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

  // ---- panels ---------------------------------------------------------------------
  function coachHTML(u) {
    var n = u.hints.length + 1;
    var body = u.hints.map(function (h) {
      return '<div class="hint"><div class="hint-lvl">Hint ' + h.level + " · " + esc(h.label) +
        (h.source === "ai" ? "" : " · coach mode") + '</div><div class="hint-txt">' + esc(h.hint) + "</div></div>";
    }).join("");
    if (u.hintBusy) body += '<div class="sel-status"><span class="spin"></span>The AI Companion is looking at the radiograph…</div>';
    else if (n <= 3) body += '<div><button class="btn-ghost" id="hint-next">' + I_AI + " Get hint " + n + " · " + HINT_LABEL[n] + "</button></div>";
    else body += '<div class="pts">All three hints used — now draw your box.</div>';
    return '<div class="coach"><div class="coach-head">' + I_AI + '<span class="t">AI Companion · coaching</span>' +
      '<span class="st">Learning Framework · 3 levels</span></div><div class="coach-body">' + body + "</div></div>";
  }

  function companionHTML(u) {
    if (!u.compOpen) return '<div class="q-actions" style="margin-top:12px"><button class="btn-ghost" id="comp-toggle">' + I_AI + " Ask the AI Companion</button></div>";
    var st = u.compSource === "ai" ? "Live · Claude" : (u.compSource ? "Coach mode" : "sees your radiograph & box");
    return '<div class="tutor" id="companion"><div class="tutor-head">' + I_AI + '<span class="t">AI Companion</span>' +
      '<span class="st" id="comp-status">' + esc(st) + '</span></div><div class="tutor-log" id="comp-log"></div>' +
      '<div class="tutor-in"><input id="comp-input" placeholder="Ask about what you see, or explain your reasoning…" autocomplete="off">' +
      '<button class="btn-primary" id="comp-send">Send</button></div></div>';
  }
  function renderCompLog() {
    var u = U(), log = document.getElementById("comp-log"); if (!log) return;
    log.innerHTML = u.chat.map(function (m) {
      var ai = m.role === "assistant";
      return '<div class="msg ' + (ai ? "ai" : "me") + '"><div class="who">' + (ai ? "AI" : "You") + '</div><div class="bub">' + esc(m.content) + "</div></div>";
    }).join("") + (u.compBusy ? '<div class="msg ai think"><div class="who">AI</div><div class="bub">looking at the radiograph…</div></div>' : "");
    if (!u.chat.length && !u.compBusy) log.innerHTML = '<div class="pts">I can see this radiograph and the region you marked. Ask me about a feature, or tell me your reasoning and I\'ll push back.</div>';
    log.scrollTop = log.scrollHeight;
  }

  // ---- render ----------------------------------------------------------------------
  function render() {
    preloadNext(state.idx);
    var c = CASES[state.idx], s = c.steps[state.sub], rec = records[state.idx][state.sub], u = U();
    var locked = rec != null && rec.ok !== undefined;   // tooth step may hold a partial pick
    var auto = (s.kind === "faculty");
    var complete = locked || auto;
    if (auto && !locked) records[state.idx][state.sub] = { ok: true };

    var q = '<div class="p4-q"><div class="p4-qhead"><span class="keyline"></span>' +
      '<span class="qstep">Step ' + s.n + " · " + (KIND_LABEL[s.kind] || s.kind) + "</span>" +
      '<span class="objtag"><span class="mastery">Obj ' + esc(s.objective) + "</span></span></div>" +
      '<div class="p4-qbody"><div class="p4-prompt">' + esc(s.prompt) + "</div>";

    if (s.kind === "area") {
      if (!locked && u.evaluating) {
        q += '<div class="sel-status"><span class="spin"></span>The AI Companion is reviewing your region on the radiograph…</div>';
      } else if (!locked) {
        q += '<div class="pts">Drag on the radiograph to draw a box around the area you would evaluate first. The AI Companion checks your selection against the image.</div>';
        if (u.box) q += '<div class="sel-status">' + I_BOX + " Box drawn — submit when ready, or draw again to adjust.</div>";
        q += '<div class="sel-tools"><button class="btn-primary" id="sel-submit"' + (u.box ? "" : " disabled") + '>Submit region ' + I_ARROW + "</button>" +
          (u.box ? '<button class="btn-ghost" id="sel-clear">Clear</button>' : "") +
          '<button class="btn-ghost" id="coach-toggle">' + I_AI + (u.coachOpen ? " Hide coaching" : " I'm not sure · get a hint") + "</button></div>";
        if (u.coachOpen) q += coachHTML(u);
      } else {
        var vmap = { hit: ["ok", "On target"], partial: ["mid", "Close — partially captured"],
                     miss: ["no", "Not quite there"], placed: ["ok", "Region recorded"] };
        var vm = vmap[rec.verdict] || vmap.placed;
        q += '<div class="feedback ' + vm[0] + '"><div class="lead">' + (vm[0] === "no" ? I_X : I_CHECK) + vm[1] +
          '<span class="verdict-pts">+' + rec.pts + " / " + s.points + " pts</span></div><div>" + esc(rec.feedback) +
          (rec.direction ? " <b>Look at:</b> " + esc(rec.direction) : "") + "</div>" +
          (rec.source === "ai" ? '<div class="pts" style="margin-top:6px">Graded by the AI Companion from the radiograph</div>' : "") + "</div>";
        if (rec.verdict === "miss" && u.redraws < 1)
          q += '<div class="q-actions" style="margin-top:10px"><button class="btn-ghost" id="sel-redraw">' + I_BOX + " Redraw · one retry</button></div>";
      }
    } else if (s.kind === "tooth") {
      var t = rec || {};
      q += '<div class="p4-sub">Tooth</div><div class="choices--two" style="margin-bottom:10px">' +
        choices(s.tooth_options, function (o) { return o === s.tooth; }, t.tooth, locked) + "</div>";
      if (s.needs_surface) {
        q += '<div class="p4-sub">Surface / region</div><div class="choices--two">' +
          choices(s.surface_options, function (o) { return o === s.surface; }, t.surface, locked) + "</div>";
      }
      if (locked) q += fb(rec.ok, esc(s.feedback));
      q += companionHTML(u);
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
      q += companionHTML(u);
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
      q += companionHTML(u);
    }

    if (complete) {
      var last = state.idx === CASES.length - 1 && state.sub === c.steps.length - 1;
      var lastInCase = state.sub === c.steps.length - 1;
      q += '<div class="q-actions"><span class="spacer"></span><button class="btn-primary" id="next">' +
        (last ? "See results " + I_ARROW : lastInCase ? "Next case " + I_ARROW : "Continue " + I_ARROW) + "</button></div>";
    }
    q += "</div></div>";

    var selectable = s.kind === "area" && !locked && !u.evaluating;
    var shownBox = (s.kind === "area" && !locked) ? u.box : (records[state.idx][0] && records[state.idx][0].box) || u.box;
    app.innerHTML = '<div class="p4-body">' + viewer(c, selectable, shownBox) + '<div id="qcol">' + q + "</div></div>";
    wire();
    renderCompLog();
    updateChrome();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // ---- selection drawing ------------------------------------------------------------
  function clamp(v) { return Math.max(0, Math.min(100, v)); }
  function r1(v) { return Math.round(v * 10) / 10; }
  function boxFrom(a, b) { return { x: r1(Math.min(a.x, b.x)), y: r1(Math.min(a.y, b.y)),
    w: r1(Math.abs(a.x - b.x)), h: r1(Math.abs(a.y - b.y)) }; }

  function wireSelection() {
    var layer = document.getElementById("sel-layer"), sel = document.getElementById("sel");
    if (!layer || !sel) return;
    var u = U(), start = null;
    function pct(ev) { var r = layer.getBoundingClientRect();
      if (!(r.width > 0 && r.height > 0)) return null;   // image not laid out yet
      return { x: clamp((ev.clientX - r.left) / r.width * 100), y: clamp((ev.clientY - r.top) / r.height * 100) }; }
    function paint(b, drag) { sel.style.display = "block"; sel.style.left = b.x + "%"; sel.style.top = b.y + "%";
      sel.style.width = b.w + "%"; sel.style.height = b.h + "%"; sel.className = drag ? "sel drag" : "sel"; }
    layer.addEventListener("pointerdown", function (ev) {
      ev.preventDefault();
      try { layer.setPointerCapture(ev.pointerId); } catch (e) {}
      start = pct(ev); if (!start) return;
      paint({ x: start.x, y: start.y, w: 0, h: 0 }, true);
    });
    layer.addEventListener("pointermove", function (ev) { var p = start && pct(ev); if (p) paint(boxFrom(start, p), true); });
    layer.addEventListener("pointerup", function (ev) {
      if (!start) return;
      var p = pct(ev), b = p ? boxFrom(start, p) : null; start = null;
      if (!b || !(b.w >= 3 && b.h >= 3)) {   // a click, not a drag (NaN-safe)
        if (u.box) paint(u.box, false); else sel.style.display = "none";
        var h = document.querySelector(".m5-hint"); if (h) h.textContent = "Drag (don't click) to draw a box around the area";
        return;
      }
      u.box = b; render();
    });
    layer.addEventListener("pointercancel", function () { start = null; if (u.box) paint(u.box, false); else sel.style.display = "none"; });
  }

  // ---- AI Companion calls --------------------------------------------------------------
  function submitRegion() {
    var u = U(), ci = state.idx, si = state.sub, c = CASES[ci];
    if (!u.box || u.evaluating) return;
    u.evaluating = true; render();
    postJSON("/api/module5/region", { case_id: c.id, box: u.box }).then(function (j) {
      var pts = (j && typeof j.points === "number") ? j.points : 2;
      records[ci][si] = { ok: pts > 0, pts: pts, box: u.box, verdict: (j && j.verdict) || "placed",
        feedback: (j && j.feedback) || "", direction: (j && j.direction) || "", source: (j && j.source) || "scripted" };
      u.evaluating = false; render();
    }).catch(function () {
      records[ci][si] = { ok: true, pts: 2, box: u.box, verdict: "placed", feedback: "Region recorded.", direction: "", source: "scripted" };
      u.evaluating = false; render();
    });
  }

  function getHint() {
    var u = U(), c = CASES[state.idx], level = u.hints.length + 1;
    if (u.hintBusy || level > 3) return;
    u.hintBusy = true; render();
    postJSON("/api/module5/hint", { case_id: c.id, level: level, box: u.box }).then(function (j) {
      u.hints.push({ level: level, label: (j && j.label) || HINT_LABEL[level], hint: (j && j.hint) || "", source: (j && j.source) || "scripted" });
      u.hintBusy = false; render();
    }).catch(function () { u.hintBusy = false; render(); });
  }

  function stageFor(kind) { return kind === "ai" ? "decision" : "reasoning"; }
  function sendCompanion() {
    var u = U(), c = CASES[state.idx], s = c.steps[state.sub];
    var input = document.getElementById("comp-input"); if (!input) return;
    var msg = (input.value || "").trim(); if (!msg || u.compBusy) return;
    input.value = "";
    var history = u.chat.slice();
    u.chat.push({ role: "user", content: msg }); u.compBusy = true; renderCompLog();
    postJSON("/api/module5/companion", { case_id: c.id, stage: stageFor(s.kind), message: msg, history: history, box: u.box }).then(function (j) {
      u.compBusy = false; u.compSource = (j && j.source) || "scripted";
      u.chat.push({ role: "assistant", content: (j && j.reply) || "Let's look at the evidence together — what do you notice about the border of that area?" });
      var st = document.getElementById("comp-status"); if (st) st.textContent = u.compSource === "ai" ? "Live · Claude" : "Coach mode";
      renderCompLog();
    }).catch(function () { u.compBusy = false; u.chat.push({ role: "assistant", content: "I couldn't reach the model just now — compare the density and border of the area with the tooth beside it and try again." }); renderCompLog(); });
  }

  // ---- wiring ----------------------------------------------------------------------------
  function on(id, fn) { var el = document.getElementById(id); if (el) el.addEventListener("click", fn); }
  function wire() {
    var c = CASES[state.idx], s = c.steps[state.sub], u = U();
    wireSelection();
    on("sel-submit", submitRegion);
    on("sel-clear", function () { u.box = null; render(); });
    on("coach-toggle", function () { u.coachOpen = !u.coachOpen; render(); });
    on("hint-next", getHint);
    on("sel-redraw", function () { records[state.idx][state.sub] = null; u.box = null; u.redraws += 1; render(); });
    on("comp-toggle", function () { u.compOpen = true; render(); var i = document.getElementById("comp-input"); if (i) i.focus(); });
    on("comp-send", sendCompanion);
    var ci = document.getElementById("comp-input");
    if (ci) ci.addEventListener("keydown", function (e) { if (e.key === "Enter") sendCompanion(); });

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
          records[state.idx][state.sub] = partial;
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
    on("next", advance);
  }

  function advance() {
    var c = CASES[state.idx];
    if (state.sub < c.steps.length - 1) { state.sub += 1; render(); }
    else if (state.idx < CASES.length - 1) { state.idx += 1; state.sub = 0; render(); }
    else renderSummary();
  }

  // ---- summary ------------------------------------------------------------------------------
  function renderSummary() {
    progress.style.display = "none";
    var area = areaStats(), tooth = stat("tooth"), find = stat("select"), ai = stat("ai"), fac = stat("faculty");
    var trap = aiTrapStat(), score = earned(), hints = hintsUsed();
    var areaOk = area.hit + area.partial + area.placed;
    var objRes = {
      1: { hit: find.ok, of: find.of, note: "Primary radiographic findings identified" },
      2: { hit: tooth.ok, of: tooth.of, note: "Correct tooth and surface selected" },
      3: { hit: areaOk, of: area.of, note: (area.hit + area.partial + area.miss > 0
             ? "Regions confirmed by the AI Companion (" + area.hit + " on target · " + area.partial + " close)"
             : "Regions marked (AI grading was offline)") },
      4: { hit: find.ok, of: find.of, note: "True pathology told apart from anatomy / artifact" },
      5: { hit: ai.ok, of: ai.of, note: "Sound judgements of the AI interpretation" },
      6: { hit: ai.ok, of: ai.of, note: "Accepted, refined or challenged the AI appropriately" },
      7: { hit: ai.ok, of: ai.of, note: "Diagnostic accuracy held up through AI dialogue" + (hints ? " · " + hints + " coaching hint(s) used" : "") },
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
        (area.hit + area.partial + area.miss > 0
          ? tile(area.hit + " / " + area.of, "Regions on target", area.partial + " close · " + area.miss + " missed")
          : tile(area.placed + " / " + area.of, "Regions recorded", "AI grading was offline")) +
        tile(find.ok + " / " + find.of, "Findings", "Primary diagnosis correct") +
        tile(trap.ok + " / " + trap.of, "AI traps resisted", "Wrong AI reads not adopted") + "</div>" +
      '<div class="grid-2"><div class="card"><div class="card-head"><span class="keyline"></span><h3>Objective coverage</h3></div><div>' + rows + "</div></div>" +
      '<div style="display:flex;flex-direction:column;gap:12px">' +
        '<div class="callout">' + I_AI + '<div class="ct"><b>AI reliance.</b> You resisted <b>' + trap.ok + " of " + trap.of +
        "</b> deliberately incorrect AI interpretations" + (area.hit + area.partial + area.miss > 0
          ? ", and the AI Companion confirmed <b>" + (area.hit + area.partial) + " of " + area.of + "</b> of your marked regions from the radiographs"
          : ", and marked <b>" + area.placed + " of " + area.of + "</b> regions (AI grading was offline)") + (hints ? " (" + hints + " coaching hint" + (hints === 1 ? "" : "s") + " used)" : "") + ".</div></div>" +
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
