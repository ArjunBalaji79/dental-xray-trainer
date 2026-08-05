"""Build the interactive Module 3 dataset (Tooth Identification & Localization).

The workbook has Module 3's goal + objectives but no cases, so the cases here are
authored from standard dental radiographic anatomy (Universal numbering, root
morphology, arch/side localization). Objectives are read live from the workbook.

Run:  python build_module3.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import openpyxl

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
XLSX = PROJECT_ROOT / "ORBIT Database _6142026.xlsx"
OUT = HERE / "data" / "module3_cases.json"

P = {"arch": 1, "side": 1, "tooth": 2, "feature": 2, "adjacent": 2, "anomaly": 2}
OBJ_OF = {"tooth": 1, "side": 2, "arch": 3, "feature": 4, "adjacent": 5, "anomaly": 6}
PROMPT = {
    "arch": "Is the highlighted tooth in the maxillary or mandibular arch?",
    "side": "Using standard mounting (the patient's right is on your left), which side of the mouth is this?",
    "tooth": "Identify the highlighted tooth (Universal numbering system).",
    "feature": "Which feature best supports that identification?",
    "adjacent": "Which neighbouring tooth is indicated?",
    "anomaly": "How would you classify the highlighted tooth?",
}


def step(key, options, expected, feedback):
    return {"key": key, "answer_type": "Binary" if key in ("arch", "side") else "Single Select",
            "objective": OBJ_OF[key], "prompt": PROMPT[key], "options": options,
            "expected": expected, "feedback": feedback, "points": P[key]}


CASES = [
    {"id": "M3-01", "name": "Mandibular Left First Molar", "difficulty": 1,
     "finding": "A single posterior tooth with two roots is highlighted on a periapical radiograph.",
     "steps": [
        step("arch", ["Maxillary", "Mandibular"], "Mandibular",
             "Two roots (one mesial, one distal) and the dense inferior cortex place this in the mandible."),
        step("side", ["Right", "Left"], "Left",
             "With the patient's right on your left, this molar sits on the patient's left side."),
        step("tooth", ["#18 — Mandibular left 2nd molar", "#19 — Mandibular left 1st molar",
                       "#30 — Mandibular right 1st molar", "#20 — Mandibular left 2nd premolar"],
             "#19 — Mandibular left 1st molar",
             "The first molar is the largest posterior tooth with two well-separated roots — #19 in the lower left."),
        step("feature", ["Two roots — one mesial, one distal", "Three roots including a palatal root",
                         "A single conical root", "Roots projecting into the maxillary sinus"],
             "Two roots — one mesial, one distal",
             "Mandibular molars have two roots; maxillary molars have three (two buccal + one palatal)."),
        step("adjacent", ["#20 — 2nd premolar (mesial)", "#18 — 2nd molar (mesial)",
                          "#3 — maxillary molar", "#30 — first molar, other side"],
             "#20 — 2nd premolar (mesial)",
             "Moving toward the midline from #19 is the second premolar #20; distally is the second molar #18."),
     ]},
    {"id": "M3-02", "name": "Maxillary Right First Molar", "difficulty": 1,
     "finding": "A large posterior tooth with multiple roots is highlighted near a large radiolucent space.",
     "steps": [
        step("arch", ["Maxillary", "Mandibular"], "Maxillary",
             "Three roots (two buccal + one palatal) and superimposition of the maxillary sinus indicate the maxilla."),
        step("side", ["Right", "Left"], "Right",
             "With standard mounting, this molar lies on the patient's right side."),
        step("tooth", ["#2 — Maxillary right 2nd molar", "#3 — Maxillary right 1st molar",
                       "#14 — Maxillary left 1st molar", "#4 — Maxillary right 1st premolar"],
             "#3 — Maxillary right 1st molar",
             "The largest maxillary posterior tooth with three roots is the first molar — #3 on the upper right."),
        step("feature", ["Three roots — two buccal and one palatal", "Two roots — mesial and distal",
                         "A single long root", "No discernible roots"],
             "Three roots — two buccal and one palatal",
             "Three roots (with a palatal root) and sinus superimposition are hallmarks of a maxillary molar."),
        step("adjacent", ["#2 — 2nd molar (distal)", "#4 — 1st premolar (distal)",
                          "#5 — 2nd premolar", "#14 — first molar, other side"],
             "#2 — 2nd molar (distal)",
             "Distal to the first molar #3 (away from the midline) is the second molar #2; mesial is #4."),
     ]},
    {"id": "M3-03", "name": "Maxillary Right Canine", "difficulty": 2,
     "finding": "A single anterior tooth with a notably long root is highlighted.",
     "steps": [
        step("arch", ["Maxillary", "Mandibular"], "Maxillary",
             "The long single root and its position in the anterior maxilla identify a maxillary canine."),
        step("side", ["Right", "Left"], "Right",
             "In standard mounting this canine is on the patient's right."),
        step("tooth", ["#6 — Maxillary right canine", "#11 — Maxillary left canine",
                       "#27 — Mandibular right canine", "#7 — Maxillary right lateral incisor"],
             "#6 — Maxillary right canine",
             "The canine has the longest root and a single pointed cusp — #6 in the upper right."),
        step("feature", ["The longest single root and a pointed cusp", "Two roots and a broad crown",
                         "A short root with three cusps", "A flat incisal edge and no cusp"],
             "The longest single root and a pointed cusp",
             "Canines have the longest root of any tooth and one prominent cusp tip."),
        step("adjacent", ["#7 — lateral incisor (mesial) & #5 — 1st premolar (distal)",
                          "#7 & #8 — incisors", "#3 & #4 — molar and premolar", "#11 & #12 — opposite side"],
             "#7 — lateral incisor (mesial) & #5 — 1st premolar (distal)",
             "The canine sits between the lateral incisor (#7, mesial) and the first premolar (#5, distal)."),
     ]},
    {"id": "M3-04", "name": "Mandibular Right First Premolar", "difficulty": 2,
     "finding": "A single-rooted posterior tooth with two cusps is highlighted.",
     "steps": [
        step("arch", ["Maxillary", "Mandibular"], "Mandibular",
             "The single root and lower-arch trabecular pattern place this in the mandible."),
        step("side", ["Right", "Left"], "Right",
             "Standard mounting puts this premolar on the patient's right."),
        step("tooth", ["#28 — Mandibular right 1st premolar", "#29 — Mandibular right 2nd premolar",
                       "#21 — Mandibular left 1st premolar", "#12 — Maxillary left 1st premolar"],
             "#28 — Mandibular right 1st premolar",
             "A single-rooted, two-cusped tooth just distal to the canine is the first premolar — #28."),
        step("feature", ["A single root and typically two cusps", "Three roots and five cusps",
                         "The longest root in the arch", "A large crown with four or more cusps"],
             "A single root and typically two cusps",
             "Premolars have one root and two cusps; molars are larger with multiple roots and cusps."),
        step("adjacent", ["#29 — 2nd premolar (distal)", "#27 — canine (distal)",
                          "#30 — 1st molar (mesial)", "#21 — premolar, other side"],
             "#29 — 2nd premolar (distal)",
             "Distal to #28 is the second premolar #29; mesial is the canine #27."),
     ]},
    {"id": "M3-05", "name": "Impacted Third Molar", "difficulty": 2,
     "finding": "A posterior tooth is tilted mesially and lodged beneath the adjacent molar, unable to erupt.",
     "steps": [
        step("arch", ["Maxillary", "Mandibular"], "Mandibular",
             "The angle of impaction against the second molar and the mandibular canal nearby indicate the lower arch."),
        step("side", ["Right", "Left"], "Left",
             "In standard mounting this third molar is on the patient's left."),
        step("tooth", ["#17 — Mandibular left 3rd molar", "#16 — Maxillary left 3rd molar",
                       "#32 — Mandibular right 3rd molar", "#18 — Mandibular left 2nd molar"],
             "#17 — Mandibular left 3rd molar",
             "The most posterior mandibular tooth on the left is the third molar — #17."),
        step("anomaly", ["Impacted", "Missing", "Restored", "Normally erupted"], "Impacted",
             "A third molar tilted against the second molar and unable to erupt is impacted (here, mesioangular)."),
     ]},
    {"id": "M3-06", "name": "Restored Maxillary Molar", "difficulty": 2,
     "finding": "A sharply-defined radiopaque material fills the crown of a maxillary posterior tooth.",
     "steps": [
        step("arch", ["Maxillary", "Mandibular"], "Maxillary",
             "Three roots and sinus proximity identify a maxillary molar."),
        step("side", ["Right", "Left"], "Left",
             "In standard mounting this molar is on the patient's left."),
        step("tooth", ["#14 — Maxillary left 1st molar", "#3 — Maxillary right 1st molar",
                       "#19 — Mandibular left 1st molar", "#15 — Maxillary left 2nd molar"],
             "#14 — Maxillary left 1st molar",
             "A three-rooted maxillary molar in the upper left first-molar position is #14."),
        step("anomaly", ["Restored", "Impacted", "Missing", "Carious (untreated)"], "Restored",
             "A well-defined radiopaque mass conforming to a cavity outline is a restoration; untreated caries is radiolucent."),
     ]},
]


def parse_objectives(ws):
    for r in ws.iter_rows(values_only=True):
        if r[0] and str(r[0]).startswith("Module 3"):
            objs = []
            for line in str(r[2]).splitlines():
                line = line.strip()
                if not line:
                    continue
                text = re.sub(r"^\s*\d+\s*[\.\)]\s*", "", line).strip()
                tm = re.search(r"(?:≥|>=)\s*(\d+)\s*%", text)
                objs.append({"n": len(objs) + 1, "text": text,
                             "target": (f"≥{tm.group(1)}%" if tm else None)})
            return str(r[1]).strip(), objs
    raise SystemExit("Module 3 not found")


def main():
    wb = openpyxl.load_workbook(XLSX, data_only=True)
    goal, objectives = parse_objectives(wb["Modules"])
    for c in CASES:
        for i, s in enumerate(c["steps"], 1):
            s["n"] = i
        c["points"] = sum(s["points"] for s in c["steps"])
    data = {"module": {"number": 3, "title": "Tooth Identification and Localization",
                       "goal": goal, "objectives": objectives},
            "cases": CASES, "total_points": sum(c["points"] for c in CASES)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Wrote {OUT.relative_to(PROJECT_ROOT)}  cases={len(CASES)} pts={data['total_points']}")
    for c in CASES:
        print(f"  {c['id']}: {[s['key'] for s in c['steps']]}")


if __name__ == "__main__":
    main()
