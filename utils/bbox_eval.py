"""Bounding box evaluation: IoU, greedy matching, detection metrics.

Both student and ground-truth boxes use COCO-style [x, y, w, h] in original
image pixel coordinates. Convert from canvas-display pixels before calling
``evaluate_annotation``.
"""

from __future__ import annotations

from typing import Dict, List, Tuple


def iou(a: List[float], b: List[float]) -> float:
    """IoU of two boxes in [x, y, w, h] format."""
    ax1, ay1, ax2, ay2 = a[0], a[1], a[0] + a[2], a[1] + a[3]
    bx1, by1, bx2, by2 = b[0], b[1], b[0] + b[2], b[1] + b[3]

    inter_x1, inter_y1 = max(ax1, bx1), max(ay1, by1)
    inter_x2, inter_y2 = min(ax2, bx2), min(ay2, by2)
    if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
        return 0.0

    inter = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
    union = a[2] * a[3] + b[2] * b[3] - inter
    return inter / union if union > 0 else 0.0


def evaluate_annotation(
    student: List[Dict],
    gt: List[Dict],
    iou_thresh: float = 0.3,
) -> Dict:
    """Evaluate student annotations against ground truth.

    Each list element is a dict with at least ``bbox`` (list[x,y,w,h]) and
    ``diagnosis`` (str). GT entries may also carry ``fdi_number`` and
    ``quadrant`` for richer feedback.

    Greedy match by descending IoU; pairs above threshold are matches.
    Returns a dict with matches (with diagnosis correctness), false
    positives, false negatives, and aggregate precision/recall/diag-acc.
    """
    pairs: List[Tuple[int, int, float]] = []
    for si, s in enumerate(student):
        for gi, g in enumerate(gt):
            v = iou(s["bbox"], g["bbox"])
            if v >= iou_thresh:
                pairs.append((si, gi, v))
    pairs.sort(key=lambda p: -p[2])

    used_s, used_g = set(), set()
    matches: List[Dict] = []
    for si, gi, v in pairs:
        if si in used_s or gi in used_g:
            continue
        used_s.add(si)
        used_g.add(gi)
        s, g = student[si], gt[gi]
        same = s["diagnosis"] == g["diagnosis"]
        matches.append({
            "student_idx": si,
            "gt_idx": gi,
            "iou": round(v, 3),
            "student_diagnosis": s["diagnosis"],
            "gt_diagnosis": g["diagnosis"],
            "gt_fdi_number": g.get("fdi_number"),
            "gt_quadrant": g.get("quadrant"),
            "diagnosis_correct": same,
        })

    fp = [{"student_idx": i, **student[i]} for i in range(len(student)) if i not in used_s]
    fn = [{"gt_idx": i, **gt[i]} for i in range(len(gt)) if i not in used_g]

    diag_correct = sum(1 for m in matches if m["diagnosis_correct"])

    return {
        "iou_thresh": iou_thresh,
        "num_student": len(student),
        "num_gt": len(gt),
        "num_matched": len(matches),
        "matches": matches,
        "false_positives": fp,
        "false_negatives": fn,
        "detection_precision": (len(matches) / len(student)) if student else 0.0,
        "detection_recall": (len(matches) / len(gt)) if gt else 0.0,
        "diagnosis_accuracy_when_matched": (diag_correct / len(matches)) if matches else 0.0,
    }


def format_eval_for_socratic(report: Dict) -> str:
    """Compact human-readable summary suitable for inclusion in a Socratic prompt."""
    lines = [
        f"IoU threshold for a 'detection': {report['iou_thresh']}",
        f"Student drew {report['num_student']} boxes; ground truth has {report['num_gt']} findings.",
        f"Detected (matched): {report['num_matched']} / {report['num_gt']} "
        f"(recall={report['detection_recall']:.0%}, precision={report['detection_precision']:.0%})",
        f"Diagnosis correctness when detected: {report['diagnosis_accuracy_when_matched']:.0%}",
    ]
    if report["matches"]:
        lines.append("\nDetected findings (student vs GT):")
        for m in report["matches"]:
            mark = "✓ correct diagnosis" if m["diagnosis_correct"] else \
                f"✗ student said '{m['student_diagnosis']}' but GT is '{m['gt_diagnosis']}'"
            lines.append(
                f"  - GT tooth {m['gt_fdi_number']} ({m['gt_quadrant']}) "
                f"[{m['gt_diagnosis']}] · IoU={m['iou']} · {mark}"
            )
    if report["false_positives"]:
        lines.append("\nFalse positives (student drew, no matching GT finding):")
        for fp in report["false_positives"]:
            lines.append(f"  - Box labeled '{fp['diagnosis']}' at bbox={fp['bbox']}")
    if report["false_negatives"]:
        lines.append("\nMissed findings (GT, but student drew no overlapping box):")
        for fn in report["false_negatives"]:
            lines.append(
                f"  - Tooth {fn.get('fdi_number')} ({fn.get('quadrant')}): {fn['diagnosis']}"
            )
    return "\n".join(lines)
