"""Build the interactive Module 5 dataset from `ORBIT Database _6142026.xlsx`.

Module 5 — Radiographic Interpretation & AI Comparison — has authored
CaseBuildout flows (5 cases, 23 steps): area selection -> tooth/surface ->
primary finding -> AI-comparison decision -> faculty review.

Run:  python build_module5.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import openpyxl

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
XLSX = PROJECT_ROOT / "ORBIT Database _6142026.xlsx"
OUT = HERE / "data" / "module5_cases.json"

# Whether the AI's interpretation is actually correct for each case. Two cases
# deliberately feature a WRONG AI read — the heart of the AI-reliance objectives.
AI_CORRECT = {
    "M5-01": True,    # AI: interproximal caries #30M — matches ground truth
    "M5-02": True,    # AI: recurrent caries #19D — matches ground truth
    "M5-03": True,    # AI: early horizontal bone loss — matches ground truth
    "M5-04": False,   # AI: "contact overlap" — actually interproximal caries
    "M5-05": False,   # AI: "periapical lesion" — actually the mental foramen
}

TOOTH_POOL = ["#3", "#14", "#19", "#29", "#30"]
SURFACE_POOL = ["Mesial", "Distal", "Occlusal", "Buccal", "Lingual", "Apical"]


def _clean(s) -> str:
    return ("" if s is None else str(s)).strip()


def _rows(ws):
    return [[_clean(c) for c in r] for r in ws.iter_rows(values_only=True)
            if any(c is not None and str(c).strip() for c in r)]


def kind_of(answer_type: str, options: list) -> str:
    at = answer_type.lower()
    if "area" in at:
        return "area"
    if "odontogram" in at or "tooth" in at:
        return "tooth"
    if "faculty" in at:
        return "faculty"
    joined = " ".join(options).lower()
    if "keep my original" in joined or "accept ai" in joined:
        return "ai"
    return "select"


def parse_tooth_surface(expected: str):
    tooth = None
    m = re.search(r"#\s*(\d+)", expected)
    if m:
        tooth = "#" + m.group(1)
    surface = None
    if ";" in expected:
        tail = expected.split(";", 1)[1].strip()
        tail = re.sub(r"\b(surface|region)\b", "", tail, flags=re.I).strip()
        if tail:
            surface = tail.capitalize()
    return tooth, surface


def parse_module(ws):
    for r in _rows(ws)[1:]:
        if re.match(r"^Module\s+5\b", r[0]):
            objectives = []
            for line in r[2].splitlines():
                line = line.strip()
                if not line:
                    continue
                text = re.sub(r"^\s*\d+\s*[\.\)]\s*", "", line).strip()
                tm = re.search(r"(?:≥|>=)\s*(\d+)\s*%", text)
                objectives.append({
                    "n": len(objectives) + 1, "text": text,
                    "target": (f"≥{tm.group(1)}%" if tm else None),
                    "kind": ("improvement" if (tm and tm.group(1) == "15") else "mastery"),
                })
            title = re.sub(r"^Module\s+5\s*[:\.\-]?\s*", "", r[0].splitlines()[0]).strip()
            title = title.replace("Interpretaion", "Interpretation")
            return {"number": 5, "title": title, "goal": r[1].strip(), "objectives": objectives}
    raise SystemExit("Module 5 row not found")


def main():
    wb = openpyxl.load_workbook(XLSX, data_only=True)
    module = parse_module(wb["Modules"])

    cl = _rows(wb["CaseLibrary"])
    hdr = cl[0]
    lib = {}
    for r in cl[1:]:
        d = dict(zip(hdr, r + [""] * (len(hdr) - len(r))))
        if d.get("Case ID", "").startswith("M5"):
            lib[d["Case ID"]] = d

    keys = ["case_id", "image_ref", "step", "objective", "prompt", "student_action",
            "answer_type", "answer_options", "ai_interpretation", "expected", "points",
            "feedback", "data_captured", "difficulty", "adaptive_tag", "ai_compat",
            "ex_correct", "ex_why", "ex_pitfall", "ex_teaching", "ex_pearls"]
    by_case = {}
    for r in _rows(wb["CaseBuildout"])[1:]:
        if not (r and r[0].startswith("M5")):
            continue
        d = dict(zip(keys, (r + [""] * len(keys))[:len(keys)]))
        opts = d["answer_options"]
        d["answer_options"] = ([o.strip() for o in opts.split(";") if o.strip()]
                               if opts and opts.upper() not in ("N/A", "NA") else [])
        d["points"] = int(d["points"]) if d["points"].isdigit() else 0
        d["step"] = int(d["step"]) if d["step"].isdigit() else 0
        by_case.setdefault(d["case_id"], []).append(d)

    cases = []
    for cid in sorted(by_case):
        raw = sorted(by_case[cid], key=lambda s: s["step"])
        meta = lib.get(cid, {})
        ai_ok = AI_CORRECT.get(cid, True)
        steps = []
        for s in raw:
            k = kind_of(s["answer_type"], s["answer_options"])
            step = {
                "n": s["step"], "kind": k, "objective": s["objective"],
                "answer_type": s["answer_type"], "prompt": s["prompt"],
                "options": s["answer_options"], "expected": s["expected"],
                "feedback": s["feedback"], "points": s["points"],
                "ai_interpretation": s["ai_interpretation"],
            }
            if k == "tooth":
                tooth, surface = parse_tooth_surface(s["expected"])
                step["tooth"] = tooth
                step["surface"] = surface
                step["tooth_options"] = sorted(set(TOOTH_POOL + ([tooth] if tooth else [])),
                                               key=lambda t: int(t[1:]))
                step["surface_options"] = (SURFACE_POOL if not surface or surface in SURFACE_POOL
                                           else SURFACE_POOL + [surface])
                step["needs_surface"] = surface is not None
            if k == "ai":
                # Correct behaviour: never adopt a wrong AI read; keep your correct one.
                step["ai_correct"] = ai_ok
                step["correct_options"] = (["Accept AI interpretation", "Keep my original interpretation"]
                                           if ai_ok else ["Keep my original interpretation"])
            if k == "faculty":
                step["expert"] = {
                    "correct": s["ex_correct"], "why": s["ex_why"], "pitfall": s["ex_pitfall"],
                    "teaching": s["ex_teaching"], "pearls": s["ex_pearls"],
                }
            steps.append(step)

        cases.append({
            "id": cid,
            "name": meta.get("Case Name", cid),
            "difficulty": int(meta["Difficulty"]) if meta.get("Difficulty", "").isdigit() else None,
            "ground_truth": meta.get("Ground Truth", ""),
            "notes": meta.get("Notes", ""),
            "ai_correct": ai_ok,
            "steps": steps,
            "points": sum(s["points"] for s in steps),
        })

    data = {"module": module, "cases": cases,
            "total_points": sum(c["points"] for c in cases)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Wrote {OUT.relative_to(PROJECT_ROOT)}")
    print(f"  cases={len(cases)} total_points={data['total_points']}")
    for c in cases:
        print(f"  {c['id']}: {len(c['steps'])} steps "
              f"[{', '.join(s['kind'] for s in c['steps'])}] AI_correct={c['ai_correct']}")


if __name__ == "__main__":
    main()
