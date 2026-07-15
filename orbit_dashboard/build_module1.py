"""Build the interactive Module 1 dataset from `ORBIT Database _6142026.xlsx`.

Module 1 — Image Quality & Error Correction — already has fully-authored
CaseBuildout flows in the workbook (9 cases, 5 steps each: diagnostic quality →
error → cause → correction → visual comparison). This script reads those real
steps and emits `data/module1_cases.json`, adding a neutral "finding" description
and modality per case (the workbook's Image Reference is still TBD).

Run:  python build_module1.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import openpyxl

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
XLSX = PROJECT_ROOT / "ORBIT Database _6142026.xlsx"
OUT = HERE / "data" / "module1_cases.json"

# Neutral appearance descriptions — describe what is SEEN without naming the
# error (the learner names it in step 2). Authored from standard radiography.
FINDINGS = {
    "M1-02": "The proximal contacts of the posterior teeth are superimposed — the enamel surfaces overlap and the interproximal areas cannot be evaluated.",
    "M1-03": "The teeth appear elongated: the roots are projected markedly longer than their true anatomic length.",
    "M1-04": "The teeth appear foreshortened — short and stubby, with the roots projected shorter than their true length.",
    "M1-05": "Tooth margins and the trabecular pattern are blurred and smeared, with loss of sharp detail across the image.",
    "M1-06": "The image is uniformly too light (low density); structures appear faint and washed-out.",
    "M1-07": "The image is uniformly too dark (high density); detail is lost within the dense areas.",
    "M1-08": "A herringbone / tyre-track pattern is superimposed over the image, which also appears unusually light.",
    "M1-09": "A blank, unexposed curved region cuts across part of the film, clipping the anatomy at one edge.",
    "M1-10": "The premolar proximal contacts are overlapped, obscuring the interproximal surfaces where caries would be seen.",
}

# One-line clinical pearl per case (shown after the visual-comparison step).
PEARLS = {
    "M1-02": "Open contacts require the beam to pass perpendicular to the buccal surfaces — correct horizontal angulation.",
    "M1-03": "Elongation = vertical angulation too shallow. Increase vertical angulation to shorten the image.",
    "M1-04": "Foreshortening = vertical angulation too steep. Decrease vertical angulation to lengthen the image.",
    "M1-05": "Motion blur is unrecoverable — stabilize the patient and receptor and retake.",
    "M1-06": "A light image usually means underexposure — increase mAs/exposure time (or check kVp).",
    "M1-07": "A dark image usually means overexposure — reduce exposure settings.",
    "M1-08": "The herringbone pattern means the receptor was placed backwards — reposition it emulsion-side to the beam.",
    "M1-09": "Cone cut = the beam missed part of the receptor — center the PID over the whole receptor.",
    "M1-10": "Overlap hides interproximal caries — reangle horizontally so contacts open before diagnosing.",
}

STEP_KEYS = {1: "diagnostic", 2: "error", 3: "cause", 4: "correction", 5: "compare"}
STEP_OBJ = {1: 1, 2: 2, 3: 3, 4: 4, 5: 6}  # primary objective each step trains


def _clean(s) -> str:
    return ("" if s is None else str(s)).strip()


def _rows(ws):
    return [[_clean(c) for c in r] for r in ws.iter_rows(values_only=True)
            if any(c is not None and str(c).strip() for c in r)]


def _opt_match(expected: str, options: list) -> bool:
    """True if `expected` corresponds to one of the options (word-boundary match)."""
    e = f" {expected.lower().strip()} "
    return any(o.strip() and f" {o.lower().strip()} " in e for o in options)


def modality(name: str) -> str:
    if re.search(r"\bBW\b", name):
        return "Bitewing"
    if re.search(r"\bPA\b", name):
        return "Periapical"
    if "Overlapped Premolar" in name:
        return "Bitewing"
    return "Intraoral"


def parse_module(ws):
    for r in _rows(ws)[1:]:
        m = re.match(r"^Module\s+1\b", r[0])
        if m:
            objectives = []
            for line in r[2].splitlines():
                line = line.strip()
                if not line:
                    continue
                text = re.sub(r"^\s*\d+\s*[\.\)]\s*", "", line).strip()
                tm = re.search(r"(?:≥|>=)\s*(\d+)\s*%", text)
                objectives.append({"n": len(objectives) + 1, "text": text,
                                   "target": (f"≥{tm.group(1)}%" if tm else None)})
            return {"number": 1, "title": "Image Quality and Error Correction",
                    "goal": r[1].strip(), "objectives": objectives}
    raise SystemExit("Module 1 row not found")


def main():
    wb = openpyxl.load_workbook(XLSX, data_only=True)
    module = parse_module(wb["Modules"])

    # case library (metadata)
    cl_rows = _rows(wb["CaseLibrary"])
    cl_hdr = cl_rows[0]
    lib = {}
    for r in cl_rows[1:]:
        d = dict(zip(cl_hdr, r + [""] * (len(cl_hdr) - len(r))))
        cid = d.get("Case ID", "")
        if cid.startswith("M1"):
            lib[cid] = d

    # buildout steps
    cb_rows = _rows(wb["CaseBuildout"])
    keys = ["case_id", "image_ref", "step", "objective", "prompt", "student_action",
            "answer_type", "answer_options", "ai_interpretation", "expected", "points",
            "feedback", "data_captured", "difficulty", "adaptive_tag", "ai_compat"]
    steps_by_case = {}
    for r in cb_rows[1:]:
        if not (r and r[0].startswith("M1")):
            continue
        d = dict(zip(keys, (r + [""] * len(keys))[:len(keys)]))
        opts = d["answer_options"]
        d["answer_options"] = ([o.strip() for o in opts.split(";") if o.strip()]
                               if opts and opts.upper() not in ("N/A", "NA") else [])
        d["points"] = int(d["points"]) if d["points"].isdigit() else 0
        d["step"] = int(d["step"]) if d["step"].isdigit() else 0
        steps_by_case.setdefault(d["case_id"], []).append(d)

    cases = []
    for cid in sorted(steps_by_case):
        raw_steps = sorted(steps_by_case[cid], key=lambda s: s["step"])
        meta = lib.get(cid, {})
        name = meta.get("Case Name", cid)
        ground_truth = meta.get("Ground Truth", "")
        steps = []
        for s in raw_steps:
            expected = s["expected"]
            # Reconcile: the error step's stored answer is sometimes a generic
            # category ("Exposure error") or a verbose note. When the case's clean
            # Ground Truth is itself one of the options, use it as the canonical,
            # selectable answer (e.g. "Underexposure", "Herringbone artifact").
            if s["answer_options"] and ground_truth and _opt_match(ground_truth, s["answer_options"]):
                expected = ground_truth
            # Canonicalize any remaining verbose answer to the exact option it contains.
            if s["answer_options"] and expected not in s["answer_options"]:
                ee = f" {expected.lower().strip()} "
                match = next((o for o in s["answer_options"]
                              if o.strip() and f" {o.lower().strip()} " in ee), None)
                if match:
                    expected = match
            steps.append({
                "n": s["step"],
                "key": STEP_KEYS.get(s["step"], "step"),
                "objective": STEP_OBJ.get(s["step"], s["objective"]),
                "answer_type": s["answer_type"],
                "prompt": s["prompt"],
                "options": s["answer_options"],
                "expected": expected,
                "feedback": s["feedback"],
                "points": s["points"],
            })
        cases.append({
            "id": cid,
            "name": name,
            "modality": modality(name),
            "difficulty": int(meta["Difficulty"]) if meta.get("Difficulty", "").isdigit() else None,
            "ground_truth": meta.get("Ground Truth", ""),
            "notes": meta.get("Notes", ""),
            "finding": FINDINGS.get(cid, ""),
            "pearl": PEARLS.get(cid, ""),
            "steps": steps,
            "points": sum(s["points"] for s in steps),
        })

    data = {"module": module, "cases": cases,
            "total_points": sum(c["points"] for c in cases)}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Wrote {OUT.relative_to(PROJECT_ROOT)}")
    print(f"  cases={len(cases)}  total_points={data['total_points']}")
    print(f"  steps/case={ {c['id']: len(c['steps']) for c in cases} }")


if __name__ == "__main__":
    main()
