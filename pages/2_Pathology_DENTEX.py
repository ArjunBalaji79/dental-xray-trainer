"""DENTEX Practice: Panoramic X-rays with real ground-truth annotations.

Uses the DENTEX dataset (MICCAI 2023) — 50 panoramic radiographs with
tooth-level bounding boxes, FDI numbering, and pathology labels
(Caries, Deep Caries, Periapical Lesion, Impacted).

UI: pick a pathology, then click two opposite corners on the X-ray to
draw a box. Boxes render server-side via PIL, so we don't depend on a
canvas iframe component.
"""

import streamlit as st
from PIL import Image, ImageDraw
from streamlit_image_coordinates import streamlit_image_coordinates

from utils.bbox_eval import evaluate_annotation, format_eval_for_socratic
from utils.dentex_loader import (
    DIAGNOSES,
    DIAGNOSIS_COLORS,
    draw_annotations,
    get_dentex_cases,
)
from utils.socratic_chat import render_socratic, start_socratic

st.set_page_config(page_title="DENTEX Practice", page_icon="🦷", layout="wide")

st.title("DENTEX Practice — Panoramic X-rays with Ground Truth")
st.markdown(
    "Practice on **real panoramic radiographs** from the DENTEX dataset (MICCAI 2023). "
    "Each image has expert-verified **tooth-level annotations** with FDI numbering and pathology labels."
)

# Auto-load Anthropic key from secrets so deep-linking this page still works
if not st.session_state.get("anthropic_api_key"):
    try:
        _key = st.secrets.get("ANTHROPIC_API_KEY", "")
        if _key:
            st.session_state["anthropic_api_key"] = _key
    except Exception:
        pass

# Load cases
cases = get_dentex_cases()
if not cases:
    st.error(
        "DENTEX dataset not found. Make sure `datasets/dentex/validation_triple.json` "
        "and `datasets/dentex/validation_data/` (unzipped images) exist."
    )
    st.stop()

# Filter by diagnosis
with st.sidebar:
    st.header("Filter Cases")
    diag_filter = st.multiselect(
        "Filter by pathology",
        list(DIAGNOSES.values()),
        default=[],
        help="Leave empty to show all cases",
    )

    if diag_filter:
        filtered = [c for c in cases if any(d in c["diagnoses_present"] for d in diag_filter)]
    else:
        filtered = cases

    if not filtered:
        st.warning("No cases match the filter.")
        st.stop()

    case_idx = st.selectbox(
        "Select a case",
        range(len(filtered)),
        format_func=lambda i: f"Case {i + 1} ({filtered[i]['file_name']}) — {len(filtered[i]['annotations'])} findings",
    )

case = filtered[case_idx]

if not case["image_path"].exists():
    st.error(
        f"Image file not found: `{case['image_path']}`\n\n"
        "Unzip `validation_data.zip` into `datasets/dentex/validation_data/`."
    )
    st.stop()

pil_image = Image.open(case["image_path"]).convert("RGB")

st.subheader(f"Case: {case['file_name']}")

DIAG_LIST = ["Caries", "Deep Caries", "Periapical Lesion", "Impacted"]

img_id = case["image_id"]
active_key = f"dentex_active_diag_{img_id}"
boxes_key = f"dentex_boxes_{img_id}"
pending_key = f"dentex_pending_{img_id}"
last_click_key = f"dentex_last_click_{img_id}"

st.session_state.setdefault(active_key, "Caries")
st.session_state.setdefault(boxes_key, [])
st.session_state.setdefault(pending_key, None)
st.session_state.setdefault(last_click_key, None)

st.markdown(
    "**Identify all pathological findings.** "
    "Pick a pathology, then click two opposite corners on the X-ray to draw a box. "
    "Use Undo to remove the most recent box, or Clear to start over."
)

# Diagnosis picker + tools row
pick_cols = st.columns(len(DIAG_LIST) + 2)
for i, diag in enumerate(DIAG_LIST):
    is_active = st.session_state[active_key] == diag
    if pick_cols[i].button(
        ("● " if is_active else "○ ") + diag,
        key=f"dentex_pick_{img_id}_{diag}",
        type="primary" if is_active else "secondary",
        use_container_width=True,
    ):
        st.session_state[active_key] = diag
        st.session_state[pending_key] = None
        st.rerun()

if pick_cols[len(DIAG_LIST)].button(
    "↶ Undo",
    key=f"dentex_undo_{img_id}",
    use_container_width=True,
    help="Cancel a pending corner, or remove the most recent box",
):
    if st.session_state[pending_key] is not None:
        st.session_state[pending_key] = None
    elif st.session_state[boxes_key]:
        st.session_state[boxes_key].pop()
    st.rerun()

if pick_cols[len(DIAG_LIST) + 1].button(
    "🗑️ Clear",
    key=f"dentex_clear_{img_id}",
    use_container_width=True,
):
    st.session_state[boxes_key] = []
    st.session_state[pending_key] = None
    st.session_state[last_click_key] = None
    st.rerun()

active_diag = st.session_state[active_key]
stroke_color = DIAGNOSIS_COLORS[active_diag]

# Render image with all current boxes drawn on it (in ORIGINAL pixel coords)
display_img = pil_image.copy()
draw = ImageDraw.Draw(display_img)

# Outline thickness scales with image so it stays visible after display downscaling
outline_w = max(4, case["width"] // 250)
marker_r = max(8, case["width"] // 180)

for box in st.session_state[boxes_key]:
    color = DIAGNOSIS_COLORS[box["diagnosis"]]
    x, y, w, h = box["bbox"]
    draw.rectangle([x, y, x + w, y + h], outline=color, width=outline_w)

if st.session_state[pending_key] is not None:
    cx, cy = st.session_state[pending_key]
    draw.ellipse(
        [cx - marker_r, cy - marker_r, cx + marker_r, cy + marker_r],
        outline=stroke_color,
        width=outline_w,
    )

DISPLAY_WIDTH = 900
scale = DISPLAY_WIDTH / case["width"]

click = streamlit_image_coordinates(
    display_img,
    width=DISPLAY_WIDTH,
    key=f"dentex_click_{img_id}",
)

if click is not None and click != st.session_state[last_click_key]:
    st.session_state[last_click_key] = click
    ox = click["x"] / scale
    oy = click["y"] / scale
    if st.session_state[pending_key] is None:
        st.session_state[pending_key] = (ox, oy)
    else:
        x1, y1 = st.session_state[pending_key]
        bx, by = min(x1, ox), min(y1, oy)
        bw, bh = abs(ox - x1), abs(oy - y1)
        if bw > 5 and bh > 5:
            st.session_state[boxes_key].append({
                "diagnosis": active_diag,
                "bbox": [bx, by, bw, bh],
            })
        st.session_state[pending_key] = None
    st.rerun()

student_boxes = st.session_state[boxes_key]

info_col, list_col = st.columns([1, 2])
with info_col:
    st.metric("Boxes drawn", len(student_boxes))
    st.caption(f"Active: **{active_diag}**")
    if st.session_state[pending_key] is not None:
        st.caption("✓ First corner placed — click second corner")
    else:
        st.caption("Click first corner to start a box")
with list_col:
    if student_boxes:
        with st.expander(f"Drawn boxes ({len(student_boxes)})", expanded=False):
            for i, b in enumerate(student_boxes):
                x, y, w, h = (int(v) for v in b["bbox"])
                st.markdown(
                    f"{i + 1}. **{b['diagnosis']}** — ({x}, {y}) · {w}×{h} px"
                )
    else:
        st.info("Click two corners on the X-ray to draw a box.")

# ---- Diagnosis writeup form ----
with st.form(f"dentex_unified_{img_id}"):
    st.markdown("**Write up your assessment:**")
    findings_answer = st.text_area(
        "Findings (describe each box's location and reasoning)",
        placeholder="e.g., Tooth 48 — impacted, horizontal orientation\n"
                    "Tooth 36 — radiolucency on mesial suggestive of caries...",
    )
    diag_answer = st.multiselect(
        "Diagnoses present in this image",
        ["Caries", "Deep Caries", "Periapical Lesion", "Impacted", "Bone Loss", "Other"],
        key=f"dentex_diag_select_{img_id}",
    )
    impression = st.text_area(
        "Overall impression",
        placeholder="e.g., Panoramic radiograph showing multiple carious lesions and "
                    "one impacted third molar...",
    )
    confidence = st.slider(
        "Confidence (1-5)", 1, 5, 3, key=f"dentex_unified_conf_{img_id}"
    )
    submitted = st.form_submit_button("Submit for Feedback", type="primary")

unified_chat_key = f"dentex_chat_unified_{img_id}"
last_eval_key = f"dentex_unified_eval_{img_id}"

if submitted:
    if not student_boxes:
        st.warning("Draw at least one bounding box before submitting.")
    elif not st.session_state.get("anthropic_api_key"):
        st.warning("Anthropic API key missing — set ANTHROPIC_API_KEY in .streamlit/secrets.toml.")
    else:
        report = evaluate_annotation(student_boxes, case["annotations"], iou_thresh=0.3)
        st.session_state[last_eval_key] = report

        findings_detail = "\n".join(
            f"  - Tooth {a['fdi_number']} ({a['quadrant']}): {a['diagnosis']}"
            for a in case["annotations"]
        )
        student_box_summary = "\n".join(
            f"  - Box {i + 1}: '{b['diagnosis']}', "
            f"bbox≈[{int(b['bbox'][0])},{int(b['bbox'][1])},"
            f"{int(b['bbox'][2])},{int(b['bbox'][3])}]"
            for i, b in enumerate(student_boxes)
        )
        correct_diags = ", ".join(case["diagnoses_present"])
        context = (
            f"Expert-verified panoramic radiograph ground truth "
            f"({len(case['annotations'])} findings):\n{findings_detail}\n"
            f"Diagnoses present: {correct_diags}\n\n"
            "Student drew bounding boxes AND wrote a free-text diagnosis. An "
            "automated evaluator computed IoU between every student box and every "
            "ground-truth finding (greedy match, IoU>=0.3 counts as a detection):\n"
            f"{format_eval_for_socratic(report)}\n\n"
            "Use FDI numbering. Caries vs deep caries, impacted teeth, and "
            "periapical lesions are all distinct categories to evaluate."
        )
        initial_msg = (
            f"Student submission (confidence: {confidence}/5): "
            f"drew {len(student_boxes)} boxes.\n\n"
            f"BOXES:\n{student_box_summary}\n\n"
            "AUTOMATED METRICS (IoU≥0.3):\n"
            f"- Detection recall:    {report['detection_recall']:.0%} "
            f"({report['num_matched']}/{report['num_gt']} findings detected)\n"
            f"- Detection precision: {report['detection_precision']:.0%} "
            f"({report['num_matched']}/{report['num_student']} boxes hit a finding)\n"
            f"- Diagnosis accuracy when matched: "
            f"{report['diagnosis_accuracy_when_matched']:.0%}\n\n"
            f"FREE-TEXT FINDINGS:\n{findings_answer or '(none)'}\n\n"
            f"DIAGNOSES SELECTED: {', '.join(diag_answer) if diag_answer else 'none'}\n\n"
            f"OVERALL IMPRESSION:\n{impression or '(none)'}"
        )
        start_socratic(unified_chat_key, context, initial_msg, case["summary"])

last_report = st.session_state.get(last_eval_key)
if last_report:
    m1, m2, m3 = st.columns(3)
    m1.metric(
        "Detection Recall",
        f"{last_report['detection_recall']:.0%}",
        help=f"{last_report['num_matched']} / {last_report['num_gt']} GT findings detected",
    )
    m2.metric(
        "Precision",
        f"{last_report['detection_precision']:.0%}",
        help=f"{last_report['num_matched']} / {last_report['num_student']} boxes hit a finding",
    )
    m3.metric(
        "Diagnosis Accuracy",
        f"{last_report['diagnosis_accuracy_when_matched']:.0%}",
        help="of detections that matched a GT finding",
    )
    with st.expander("Show your boxes vs ground truth", expanded=False):
        gt_overlay = draw_annotations(pil_image, case["annotations"])
        st.image(gt_overlay, use_container_width=True, caption="Ground truth annotations")

render_socratic(unified_chat_key)

st.divider()
if "dentex_completed" not in st.session_state:
    st.session_state["dentex_completed"] = set()
if submitted:
    st.session_state["dentex_completed"].add(img_id)
completed = len(st.session_state.get("dentex_completed", set()))
st.progress(completed / len(cases), text=f"Progress: {completed}/{len(cases)} DENTEX cases attempted")
