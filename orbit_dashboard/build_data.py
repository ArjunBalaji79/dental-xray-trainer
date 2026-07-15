"""Build a clean, normalized JSON dataset for the ORBIT dashboard.

Reads the source workbook `ORBIT Database (1).xlsx` (five sheets: Modules,
InteractionDesign, CaseLibrary, CaseBuildout, ReferenceListsDifficulty) and emits
`data/orbit.json` — the file the Flask app loads at startup.

Run from anywhere:  python build_data.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import openpyxl

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
XLSX = PROJECT_ROOT / "ORBIT Database (1).xlsx"
OUT = HERE / "data" / "orbit.json"

TITLE_FIXES = {"Interpretaion": "Interpretation", "Compatiblity": "Compatibility"}

MODULE_META = {
    1: ("Image quality triage", "\U0001FA7B"),
    2: ("Mounting & orientation", "\U0001F5C2"),
    3: ("Tooth ID & localization", "\U0001F9B7"),
    4: ("Normal vs pathology", "\U0001F50D"),
    5: ("Interpretation + AI", "\U0001F916"),
    6: ("EHR charting", "\U0001F4CB"),
    7: ("Panoramic reading", "\U0001F311"),
    8: ("Advanced decisions", "\U0001F9E9"),
}


def _clean(s) -> str:
    return ("" if s is None else str(s)).strip()


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def _fix_typos(s: str) -> str:
    for bad, good in TITLE_FIXES.items():
        s = s.replace(bad, good)
    return s


def _rows(ws):
    for row in ws.iter_rows(values_only=True):
        if any(c is not None and str(c).strip() != "" for c in row):
            yield [_clean(c) for c in row]


def parse_modules(ws):
    modules = []
    rows = list(_rows(ws))[1:]
    for raw_title, description, objectives_blob in rows:
        first_line = raw_title.splitlines()[0]
        note = " ".join(raw_title.splitlines()[1:]).strip() or None
        m = re.match(r"^Module\s+(\d+)\s*[:\.\-]?\s*(.*)$", first_line)
        if m:
            number = int(m.group(1))
            title = _fix_typos(m.group(2).strip())
        else:
            number = len(modules) + 1
            title = _fix_typos(first_line.strip())

        objectives = []
        for line in objectives_blob.splitlines():
            line = line.strip()
            if not line:
                continue
            text = re.sub(r"^\s*\d+\s*[\.\)]\s*", "", line).strip()
            if not text:
                continue
            tm = re.search(r"(?:≥|>=|≤|<=)?\s*(\d+)\s*%", text)
            target = None
            if tm:
                sign_m = re.search(r"(≥|>=|≤|<=)\s*\d+\s*%", text)
                sign = sign_m.group(1) if sign_m else "≥"
                sign = {">=": "≥", "<=": "≤"}.get(sign, sign)
                target = f"{sign}{tm.group(1)}%"
            kind = "improvement" if (target and tm.group(1) == "15") else "mastery"
            objectives.append({"n": len(objectives) + 1, "text": text,
                               "target": target, "kind": kind})

        tagline, glyph = MODULE_META.get(number, ("", "\U0001FAB7"))
        modules.append({
            "number": number, "title": title,
            "slug": _slug(f"module-{number}-{title}"),
            "note": note, "tagline": tagline, "glyph": glyph,
            "description": _fix_typos(description.strip()),
            "objectives": objectives, "objective_count": len(objectives),
            "ai_enabled": "AI" in objectives_blob or "AI" in description,
        })
    modules.sort(key=lambda x: x["number"])
    return modules


def parse_interaction(ws):
    rows = list(_rows(ws))
    keys = ["module", "objective", "question_type", "student_action",
            "input_type", "correct_answer_type", "measures"]
    out = []
    for r in rows[1:]:
        r = (r + [""] * len(keys))[:len(keys)]
        out.append(dict(zip(keys, r)))
    return out


def parse_case_library(ws):
    rows = list(_rows(ws))
    keys = ["id", "module", "name", "type", "difficulty",
            "ground_truth", "question_type", "notes"]
    out = []
    for r in rows[1:]:
        r = (r + [""] * len(keys))[:len(keys)]
        d = dict(zip(keys, r))
        d["module"] = int(d["module"]) if d["module"].isdigit() else d["module"]
        d["difficulty"] = int(d["difficulty"]) if d["difficulty"].isdigit() else None
        out.append(d)
    return out


def parse_case_buildout(ws):
    rows = list(_rows(ws))
    keys = ["case_id", "image_ref", "step", "objective", "prompt", "student_action",
            "answer_type", "answer_options", "correct_answer", "points", "feedback",
            "data_captured", "difficulty", "adaptive_tag", "ai_compatibility"]
    activities, order = {}, []
    for r in rows[1:]:
        r = (r + [""] * len(keys))[:len(keys)]
        d = dict(zip(keys, r))
        cid = d["case_id"]
        if not cid:
            continue
        opts_raw = d["answer_options"]
        if opts_raw and opts_raw.upper() not in ("N/A", "NA"):
            d["answer_options"] = [o.strip() for o in opts_raw.split(";") if o.strip()]
        else:
            d["answer_options"] = []
        d["points"] = int(d["points"]) if d["points"].isdigit() else 0
        d["difficulty"] = int(d["difficulty"]) if d["difficulty"].isdigit() else None
        if cid not in activities:
            activities[cid] = []
            order.append(cid)
        activities[cid].append(d)
    for cid in activities:
        activities[cid].sort(key=lambda s: int(s["step"]) if s["step"].isdigit() else 0)
    return {"order": order, "by_case": activities}


def parse_reference(ws):
    rows = list(_rows(ws))

    def col(idx):
        return [r[idx] for r in rows[1:] if idx < len(r) and r[idx]]

    difficulty = []
    for r in rows[1:]:
        lvl = r[0] if len(r) > 0 else ""
        defn = r[1] if len(r) > 1 else ""
        if lvl and defn:
            difficulty.append({"level": int(lvl) if lvl.isdigit() else lvl, "definition": defn})
    return {
        "difficulty": difficulty,
        "adaptive_tags": col(3),
        "ai_compatible": col(5),
        "question_types": col(7),
        "case_types": col(9),
    }


def main():
    wb = openpyxl.load_workbook(XLSX, data_only=True)
    modules = parse_modules(wb["Modules"])
    interaction = parse_interaction(wb["InteractionDesign"])
    cases = parse_case_library(wb["CaseLibrary"])
    buildout = parse_case_buildout(wb["CaseBuildout"])
    reference = parse_reference(wb["ReferenceListsDifficulty"])

    for c in cases:
        steps = buildout["by_case"].get(c["id"], [])
        c["steps"] = len(steps)
        c["has_activity"] = len(steps) > 0
        c["points"] = sum(s.get("points", 0) for s in steps)

    for mod in modules:
        mod["cases"] = [c for c in cases if c["module"] == mod["number"]]
        mod["case_count"] = len(mod["cases"])
        mod["interaction"] = [x for x in interaction if x["module"] == str(mod["number"])]
        mod["authored_steps"] = sum(
            len(buildout["by_case"].get(c["id"], [])) for c in mod["cases"])

    total_objectives = sum(m["objective_count"] for m in modules)
    objectives_with_target = sum(1 for m in modules for o in m["objectives"] if o["target"])
    total_steps = sum(len(v) for v in buildout["by_case"].values())
    diff_counts = {1: 0, 2: 0, 3: 0}
    for c in cases:
        if c["difficulty"] in diff_counts:
            diff_counts[c["difficulty"]] += 1
    ai_modules = [m["number"] for m in modules if m["ai_enabled"]]

    stats = {
        "modules": len(modules),
        "objectives": total_objectives,
        "objectives_with_target": objectives_with_target,
        "cases": len(cases),
        "steps": total_steps,
        "difficulty_tiers": 3,
        "ai_modules": ai_modules,
        "ai_module_count": len(ai_modules),
        "difficulty_distribution": [
            {"level": 1, "label": "Obvious / basic", "count": diff_counts[1]},
            {"level": 2, "label": "Moderate", "count": diff_counts[2]},
            {"level": 3, "label": "Subtle / complex", "count": diff_counts[3]},
        ],
        "cases_per_module": [
            {"number": m["number"], "title": m["title"], "count": m["case_count"]}
            for m in modules],
        "objectives_per_module": [
            {"number": m["number"], "title": m["title"], "count": m["objective_count"]}
            for m in modules],
    }

    data = {
        "platform": {
            "name": "ORBIT",
            "full_name": "Oral Radiology Board-Interpretation Trainer",
            "org": "Dr. Perelman AIxEducation Project",
            "tagline": "AI-assisted dental radiology education — curriculum console",
        },
        "stats": stats, "modules": modules, "cases": cases,
        "buildout": buildout, "interaction": interaction, "reference": reference,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Wrote {OUT.relative_to(PROJECT_ROOT)}")
    print(f"  modules={stats['modules']}  objectives={stats['objectives']}  "
          f"cases={stats['cases']}  steps={stats['steps']}  ai_modules={ai_modules}")


if __name__ == "__main__":
    main()
