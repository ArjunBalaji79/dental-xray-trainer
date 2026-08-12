/* ORBIT — Module 4 interactive trainer.
   A learner works through 4 false-positive trap cases: classify -> identify ->
   justify, with scored feedback and the AI Companion (objective 7). Pure
   vanilla JS; answer-checking is client-side (fine for a teaching demo). */
(function () {
  "use strict";

  var DATA = JSON.parse(document.getElementById("m4-data").textContent);
  var CFG = window.M4CFG || { aiAvailable: false, tutorUrl: "", imgBase: "" };
  var CASES = DATA.cases;
  var OBJ = DATA.module.objectives;

  // Warm the next case's radiograph so advancing doesn't flash an empty frame.
  var preloaded = {};
  function preloadNext(idx) {
    var n = CASES[idx + 1];
    if (!n || !n.image || preloaded[n.image]) return;
    preloaded[n.image] = true;
    (new Image()).src = CFG.imgBase + n.image;
  }

  var PTS = { classify: 2, identify: 1, justify: 2 };
  var PER_CASE = PTS.classify + PTS.identify + PTS.justify; // 5
  var TOTAL_PTS = CASES.length * PER_CASE;

  var app = document.getElementById("p4-app");
  var progress = document.getElementById("p4-progress");

  // ---- session state -------------------------------------------------------
  var state, records, tutor;
  function reset() {
    state = { idx: 0, sub: "classify", answered: false };
    records = CASES.map(function () {
      return { classifyFirst: null, classifyFinal: null, cFirstOK: false, cFinalOK: false,
        overdiag: false, confidence: 3, identify: null, iOK: false,
        justify: null, jOK: false, usedTutor: false, revised: false };
    });
    tutor = CASES.map(function () { return { history: [], seeded: false, busy: false }; });
  }

  // ---- small helpers -------------------------------------------------------
  function h(html) { var t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstChild; }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function icon(path, sw) { return '<svg class="glyph" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="' + (sw || 1.6) + '" stroke-linecap="round" stroke-linejoin="round">' + path + "</svg>"; }
  var I_CHECK = icon('<path d="M20 6 9 17l-5-5"/>', 2);
  var I_X = icon('<path d="M18 6 6 18M6 6l12 12"/>', 2);
  var I_AI = icon('<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M8 12h8M8 8h8M8 16h5"/>');

  function earned() {
    var p = 0;
    records.forEach(function (r) {
      if (r.cFinalOK) p += PTS.classify;
      if (r.iOK) p += PTS.identify;
      if (r.jOK) p += PTS.justify;
    });
    return p;
  }

  function updateChrome() {
    var done = 0;
    records.forEach(function (r, i) {
      if (i < state.idx) done += 3;
      else if (i === state.idx) done += (state.sub === "classify" ? 0 : state.sub === "identify" ? 1 : 2);
    });
    var pct = Math.round((done / (CASES.length * 3)) * 100);
    var bar = document.getElementById("p4-bar"); if (bar) bar.style.width = pct + "%";
    var lab = document.getElementById("p4-lab"); if (lab) lab.textContent = "Case " + (state.idx + 1) + " of " + CASES.length;
    var sc = document.getElementById("p4-score"); if (sc) sc.textContent = earned() + " pts";
    var sbs = document.getElementById("sb-score"); if (sbs) sbs.textContent = earned() + " / " + TOTAL_PTS + " pts";
    var cCorrect = records.filter(function (r) { return r.cFinalOK; }).length;
    var cDone = records.filter(function (r) { return r.classifyFinal != null; }).length;
    var sba = document.getElementById("sb-acc"); if (sba) sba.textContent = cDone ? (cCorrect + " / " + cDone + " correct") : "—";
    document.querySelectorAll("#sb-caselist [data-caseidx]").forEach(function (nodeEl) {
      var i = +nodeEl.getAttribute("data-caseidx");
      nodeEl.className = i === state.idx ? "sb-list-item" : "sb-plain-item";
    });
  }

  // ---- viewer --------------------------------------------------------------
  function viewerHTML(c, revealFeatures) {
    var roi = c.roi || {};
    var roiEl = (roi.x != null) ? '<div class="roi" style="left:' + roi.x + '%; top:' + roi.y +
      '%; width:' + (roi.r * 2) + '%; aspect-ratio:1"></div>' : "";
    var feats = revealFeatures ? '<ul class="feat-list">' + c.features.map(function (f) {
      return "<li>" + esc(f) + "</li>"; }).join("") + "</ul>" : "";
    return '<div class="p4-view">' +
      '<div class="imgwrap"><img src="' + CFG.imgBase + esc(c.image) + '" alt="Radiograph for ' + esc(c.name) + '">' + roiEl + "</div>" +
      '<div class="vcap"><div class="roinote">Region of interest · illustrative</div>' +
      '<div class="finding">' + esc(c.finding) + "</div></div>" + feats + "</div>";
  }

  // ---- choice list ---------------------------------------------------------
  function choicesHTML(options, correct, chosen, locked) {
    return '<div class="choices">' + options.map(function (opt) {
      var cls = "choice";
      if (locked) {
        if (opt === correct) cls += " correct";
        else if (opt === chosen) cls += " wrong";
        else cls += " muted";
      } else if (opt === chosen) cls += " selected";
      var mark = (locked && opt === correct) ? I_CHECK : (locked && opt === chosen) ? I_X : "";
      var tag = locked ? (opt === correct ? '<span class="tag">Correct</span>' : (opt === chosen ? '<span class="tag">Your pick</span>' : "")) : "";
      return '<button class="' + cls + '" data-opt="' + esc(opt) + '"' + (locked ? " disabled" : "") + '>' +
        '<span class="mark">' + mark + "</span>" +
        '<span class="txt">' + esc(opt) + "</span>" + tag + "</button>";
    }).join("") + "</div>";
  }

  function feedbackHTML(ok, lead, body) {
    return '<div class="feedback ' + (ok ? "ok" : "no") + '">' +
      '<div class="lead">' + (ok ? I_CHECK : I_X) + (lead || (ok ? "Correct" : "Not quite")) + "</div>" +
      "<div>" + esc(body) + "</div></div>";
  }

  // ---- INTRO ---------------------------------------------------------------
  function renderIntro() {
    progress.style.display = "none";
    var note = DATA.module.note ? '<div class="mod-note" style="margin-top:8px">Authoring note · <b>' + esc(DATA.module.note) + "</b></div>" : "";
    app.innerHTML =
      '<div class="p4-hero">' +
        "<h1>Module 4 — Normal Anatomy vs Pathology</h1>" +
        '<div class="lead">' + esc(DATA.module.goal) + "</div>" + note +
        '<div class="obj-grid">' + OBJ.map(function (o) {
          var badge = o.target ? '<span class="mastery' + (o.kind === "improvement" ? " mastery--improve" : "") + '">' + o.target + "</span>" : "";
          return '<div class="obj-card"><div class="n">' + o.n + '</div><div><div class="t">' + esc(o.text) + "</div>" + badge + "</div></div>";
        }).join("") + "</div>" +
        '<div class="q-actions" style="margin-top:16px"><button class="btn-primary" id="p4-begin">' +
          icon('<path d="M6 4l14 8-14 8z" fill="currentColor" stroke="none"/>') + " Begin practice · " + CASES.length + " cases</button>" +
          '<span class="pts">Classify → identify → justify, with the AI Companion. ' + TOTAL_PTS + " points.</span></div>" +
      "</div>";
    document.getElementById("p4-begin").addEventListener("click", function () {
      state = { idx: 0, sub: "classify", answered: false };
      progress.style.display = "flex";
      renderCase();
    });
    updateChrome();
  }

  // ---- CASE ----------------------------------------------------------------
  function renderCase() {
    preloadNext(state.idx);
    var c = CASES[state.idx], r = records[state.idx];
    var sub = state.sub;
    var revealFeatures = (sub !== "classify") || r.classifyFinal != null;
    var q = "";
    if (sub === "classify") q = classifyPanel(c, r);
    else if (sub === "identify") q = identifyPanel(c, r);
    else q = justifyPanel(c, r);

    app.innerHTML = '<div class="p4-body">' + viewerHTML(c, revealFeatures) + '<div id="qcol">' + q + "</div></div>";
    wireCase();
    updateChrome();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function qHead(stepNo, label, objN) {
    return '<div class="p4-qhead"><span class="keyline"></span>' +
      '<span class="qstep">Step ' + stepNo + " · " + label + "</span>" +
      '<span class="objtag"><span class="mastery">Obj ' + objN + "</span></span></div>";
  }

  function classifyPanel(c, r) {
    var locked = r.classifyFinal != null;
    var chosen = r.classifyFinal || r.classifyFirst;
    var body = '<div class="p4-q">' + qHead(1, "Classify the finding", c.classify.objective) +
      '<div class="p4-qbody"><div class="p4-prompt">' + esc(c.classify.prompt) + "</div>" +
      choicesHTML(c.classify.options, c.classify.correct, chosen, locked);
    if (!locked) {
      body += '<div class="confidence"><label>How confident are you?</label>' +
        '<input type="range" id="conf" min="1" max="5" value="' + r.confidence + '">' +
        '<span class="val" id="confval">' + confLabel(r.confidence) + "</span></div>";
    }
    if (locked) {
      var ok = r.cFinalOK;
      var fb = c.classify.feedback[chosen] || (ok ? "Correct." : "Reconsider the radiographic features.");
      body += feedbackHTML(ok, ok ? "Correct classification" : "Overdiagnosis risk", fb);
      body += tutorHTML(c);
      body += '<div class="q-actions">';
      if (!ok && !r.revised) {
        body += '<button class="btn-ghost" id="revise">' + icon('<path d="M3 2v6h6"/><path d="M3 8a9 9 0 1 0 3-6.7L3 8"/>') + " Reconsider my answer</button>";
      }
      body += '<span class="spacer"></span><button class="btn-primary" id="next">Continue to identification ' +
        icon('<path d="M5 12h14M12 5l7 7-7 7"/>') + "</button></div>";
    }
    body += "</div></div>";
    return body;
  }

  function identifyPanel(c, r) {
    var locked = r.identify != null;
    var body = '<div class="p4-q">' + qHead(2, "Identify the structure", c.identify.objective) +
      '<div class="p4-qbody"><div class="p4-prompt">' + esc(c.identify.prompt) + "</div>" +
      choicesHTML(c.identify.options, c.identify.correct, r.identify, locked);
    if (locked) {
      body += feedbackHTML(r.iOK, r.iOK ? "Correct" : "Not quite",
        r.iOK ? c.identify.feedback_correct : c.identify.feedback_incorrect);
      body += '<div class="q-actions"><span class="spacer"></span><button class="btn-primary" id="next">Continue to reasoning ' +
        icon('<path d="M5 12h14M12 5l7 7-7 7"/>') + "</button></div>";
    }
    body += "</div></div>";
    return body;
  }

  function justifyPanel(c, r) {
    var locked = r.justify != null;
    var body = '<div class="p4-q">' + qHead(3, "Justify with a feature", c.justify.objective) +
      '<div class="p4-qbody"><div class="p4-prompt">' + esc(c.justify.prompt) + "</div>" +
      choicesHTML(c.justify.options, c.justify.correct, r.justify, locked);
    if (locked) {
      body += feedbackHTML(r.jOK, r.jOK ? "Good reasoning" : "Reconsider", c.justify.explain);
      var last = state.idx === CASES.length - 1;
      body += '<div class="q-actions"><span class="spacer"></span><button class="btn-primary" id="next">' +
        (last ? "See results " + icon('<path d="M5 12h14M12 5l7 7-7 7"/>') : "Next case " + icon('<path d="M5 12h14M12 5l7 7-7 7"/>')) + "</button></div>";
    }
    body += "</div></div>";
    return body;
  }

  function confLabel(v) { return ["", "Guessing", "Unsure", "Moderate", "Confident", "Certain"][v] || v; }

  // ---- wiring --------------------------------------------------------------
  function wireCase() {
    var c = CASES[state.idx], r = records[state.idx];

    var conf = document.getElementById("conf");
    if (conf) conf.addEventListener("input", function () {
      r.confidence = +conf.value;
      document.getElementById("confval").textContent = confLabel(r.confidence);
    });

    document.querySelectorAll(".choice:not([disabled])").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var opt = btn.getAttribute("data-opt");
        if (state.sub === "classify") answerClassify(c, r, opt);
        else if (state.sub === "identify") answerIdentify(c, r, opt);
        else answerJustify(c, r, opt);
      });
    });

    var next = document.getElementById("next");
    if (next) next.addEventListener("click", advance);
    var revise = document.getElementById("revise");
    if (revise) revise.addEventListener("click", function () {
      r.revised = true; r.classifyFinal = null; // re-open (keeps classifyFirst)
      renderCase();
    });
    wireTutor(c, r);
  }

  function answerClassify(c, r, opt) {
    var ok = opt === c.classify.correct;
    if (r.classifyFirst == null) { r.classifyFirst = opt; r.cFirstOK = ok; }
    r.classifyFinal = opt; r.cFinalOK = ok;
    r.overdiag = (opt === "Pathology" && c.ground_truth !== "Pathology");
    renderCase();
  }
  function answerIdentify(c, r, opt) {
    r.identify = opt; r.iOK = opt === c.identify.correct; renderCase();
  }
  function answerJustify(c, r, opt) {
    r.justify = opt; r.jOK = opt === c.justify.correct; renderCase();
  }

  function advance() {
    if (state.sub === "classify") { state.sub = "identify"; renderCase(); }
    else if (state.sub === "identify") { state.sub = "justify"; renderCase(); }
    else {
      if (state.idx === CASES.length - 1) renderSummary();
      else { state.idx += 1; state.sub = "classify"; renderCase(); }
    }
  }

  // ---- AI Companion --------------------------------------------------------
  function tutorHTML(c) {
    return '<div class="tutor" id="tutor">' +
      '<div class="tutor-head">' + I_AI + '<span class="t">AI Companion</span>' +
      '<span class="st" id="tutor-status">' + (CFG.aiAvailable ? "connecting…" : "Coach mode") + "</span></div>" +
      '<div class="tutor-log" id="tutor-log"></div>' +
      '<div class="tutor-in"><input id="tutor-input" placeholder="Ask the AI Companion or explain your reasoning…" autocomplete="off">' +
      '<button class="btn-primary" id="tutor-send">Send</button></div></div>';
  }

  function wireTutor(c, r) {
    var t = tutor[state.idx];
    var log = document.getElementById("tutor-log");
    if (!log) return;
    renderTutorLog();
    if (!t.seeded) { t.seeded = true; r.usedTutor = true; sendTutor(c, r, null); }

    function renderTutorLog() {
      log.innerHTML = t.history.map(function (m) {
        var who = m.role === "assistant" ? '<div class="who">AI</div>' : '<div class="who">You</div>';
        var cls = m.role === "assistant" ? "msg ai" : "msg me";
        return '<div class="' + cls + '">' + who + '<div class="bub">' + esc(m.content) + "</div></div>";
      }).join("") + (t.busy ? '<div class="msg ai think"><div class="who">AI</div><div class="bub">thinking…</div></div>' : "");
      log.scrollTop = log.scrollHeight;
    }

    function sendTutor(c, r, message) {
      if (message) t.history.push({ role: "user", content: message });
      t.busy = true; renderTutorLog();
      fetch(CFG.tutorUrl, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ case_id: c.id, student_answer: r.classifyFinal || r.classifyFirst,
          message: message || "", history: t.history })
      }).then(function (res) { return res.json(); }).then(function (j) {
        t.busy = false;
        t.source = j.source;
        var st = document.getElementById("tutor-status");
        if (st) st.textContent = j.source === "ai" ? "Live · Claude" : "Coach mode";
        t.history.push({ role: "assistant", content: j.reply || "(no reply)" });
        renderTutorLog();
      }).catch(function () {
        t.busy = false;
        t.history.push({ role: "assistant", content: "Trace the border and check symmetry — is this destroying bone, or is it a normal structure?" });
        renderTutorLog();
      });
    }

    var input = document.getElementById("tutor-input");
    var send = document.getElementById("tutor-send");
    function submit() {
      var v = (input.value || "").trim();
      if (!v || t.busy) return;
      input.value = "";
      sendTutor(c, r, v);
    }
    send.addEventListener("click", submit);
    input.addEventListener("keydown", function (e) { if (e.key === "Enter") submit(); });
  }

  // ---- SUMMARY -------------------------------------------------------------
  function renderSummary() {
    progress.style.display = "none";
    var n = CASES.length;
    var cFinal = records.filter(function (r) { return r.cFinalOK; }).length;
    var cFirst = records.filter(function (r) { return r.cFirstOK; }).length;
    var idOK = records.filter(function (r) { return r.iOK; }).length;
    var jOK = records.filter(function (r) { return r.jOK; }).length;
    var overdiag = records.filter(function (r) { return r.overdiag; }).length;
    var score = earned();
    var acc = Math.round((cFinal / n) * 100);
    var firstAcc = Math.round((cFirst / n) * 100);
    var gain = acc - firstAcc;

    // per-objective pass mapping
    var objRes = {
      1: { hit: cFinal, of: n, note: "Correct normal / artifact / pathology classifications" },
      2: { hit: idOK, of: n, note: "Structures correctly identified" },
      3: { hit: (n - overdiag), of: n, note: "Artifacts / normal variants not confused with pathology" },
      4: { hit: cFinal, of: n, note: "False-positive trap cases correctly resolved" },
      5: { hit: jOK, of: n, note: "Findings justified with the right radiographic feature" },
      6: { hit: (n - overdiag), of: n, note: overdiag ? (overdiag + " overdiagnosis error(s)") : "No overdiagnosis of normal anatomy" },
      7: { hit: (gain > 0 ? 1 : 0), of: 1, note: "Accuracy change after AI dialogue: " + firstAcc + "% → " + acc + "% (" + (gain >= 0 ? "+" : "") + gain + " pp)" }
    };

    function tile(num, cap, note) {
      return '<div class="kpi-tile"><div class="kpi-num tabular">' + num + '</div><div class="kpi-cap">' + cap + '</div><div class="kpi-note">' + note + "</div></div>";
    }

    var objRows = OBJ.map(function (o) {
      var res = objRes[o.n];
      var hit = res.hit >= res.of;
      var frac = res.of > 1 ? (res.hit + " / " + res.of) : "";
      return '<div class="sum-obj"><div class="ic ' + (hit ? "hit" : "miss") + '">' + (hit ? "✓" : "!") + "</div>" +
        '<div><div class="st">' + esc(o.text) + " " + (frac ? '<b class="tabular">' + frac + "</b>" : "") + "</div>" +
        '<div class="sd">' + esc(res.note) + "</div></div></div>";
    }).join("");

    app.innerHTML =
      '<div class="section-banner" style="margin-top:4px"><span class="section-kicker">Results</span><h2>Module 4 · Session Summary</h2>' +
        '<span class="sub">' + CASES.length + " trap cases completed</span></div>" +
      '<div class="sum-tiles">' +
        tile(score + " / " + TOTAL_PTS, "Score", "Classify 2 · identify 1 · justify 2") +
        tile(acc + "%", "Classification accuracy", cFinal + " of " + n + " correct") +
        tile(cFinal + " / " + n, "Traps avoided", "False-positives resolved") +
        tile(firstAcc + " → " + acc + "%", "After AI dialogue", "first attempt → after review (" + (gain >= 0 ? "+" : "") + gain + " pp)") +
      "</div>" +
      '<div class="grid-2"><div class="card"><div class="card-head"><span class="keyline"></span><h3>Objective coverage</h3></div><div>' + objRows + "</div></div>" +
      '<div style="display:flex;flex-direction:column;gap:12px">' +
        '<div class="callout">' + I_AI + '<div class="ct"><b>Objective 7 — improvement after AI dialogue.</b> Your first-attempt accuracy was ' + firstAcc + "%; after the AI Companion / annotation review it was " + acc + "%. Target is a ≥15% gain across a full case set.</div></div>" +
        (overdiag ? '<div class="feedback no" style="margin:0"><div class="lead">' + I_X + "Overdiagnosis</div><div>You classified " + overdiag + " normal/artifact finding(s) as pathology — the exact error Module 4 trains you to avoid.</div></div>"
                  : '<div class="feedback ok" style="margin:0"><div class="lead">' + I_CHECK + "No overdiagnosis</div><div>You never called a normal structure or artifact “pathology.” That is objective 6.</div></div>") +
        '<div class="card"><div class="card-body" style="display:flex;gap:8px;align-items:center"><button class="btn-primary" id="restart">' + icon('<path d="M3 2v6h6"/><path d="M3 8a9 9 0 1 0 3-6.7L3 8"/>') + ' Restart Module 4</button><a class="btn-ghost" href="/module/4">Back to Module 4</a></div></div>' +
      "</div></div>";

    document.getElementById("restart").addEventListener("click", function () { reset(); renderIntro(); });
    updateChrome();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // ---- go ------------------------------------------------------------------
  reset();
  renderIntro();
})();
