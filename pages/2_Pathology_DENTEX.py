"""DENTEX Practice: Panoramic X-rays with real ground-truth annotations.

Uses the DENTEX dataset (MICCAI 2023) — 50 panoramic radiographs with
tooth-level bounding boxes, FDI numbering, and pathology labels
(Caries, Deep Caries, Periapical Lesion, Impacted).
"""

import streamlit as st
from PIL import Image
import utils.canvas_compat  # noqa: F401  -- patches Streamlit before canvas import
from streamlit_drawable_canvas import st_canvas
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

# Check image exists
if not case["image_path"].exists():
    st.error(
        f"Image file not found: `{case['image_path']}`\n\n"
        "Unzip `validation_data.zip` into `datasets/dentex/validation_data/`."
    )
    st.stop()

pil_image = Image.open(case["image_path"])

# Display
st.subheader(f"Case: {case['file_name']}")

DIAG_LIST = ["Caries", "Deep Caries", "Periapical Lesion", "Impacted"]
MULTI_STROKE = "#FFFFFF"  # sentinel stroke color for boxes carrying >1 label

active_key = f"dentex_active_diag_{case['image_id']}"
canvas_ver_key = f"dentex_canvas_ver_{case['image_id']}"
edit_key = f"dentex_edit_mode_{case['image_id']}"
labels_key = f"dentex_box_labels_{case['image_id']}"  # pos-hash -> tuple(diagnoses)
if active_key not in st.session_state:
    st.session_state[active_key] = ["Caries"]
if canvas_ver_key not in st.session_state:
    st.session_state[canvas_ver_key] = 0
if edit_key not in st.session_state:
    st.session_state[edit_key] = False
if labels_key not in st.session_state:
    st.session_state[labels_key] = {}

active_set = set(st.session_state[active_key])

st.markdown(
    "**Identify all pathological findings.** "
    "Pick one or more pathologies, then draw a tight box around each finding. "
    "When multiple are active, a box carries all of them (use this for co-occurring "
    "findings on the same tooth). Use Edit to delete a box."
)

# Diagnosis picker (multi-select toggles) + tools row
pick_cols = st.columns(len(DIAG_LIST) + 2)
for i, diag in enumerate(DIAG_LIST):
    is_active = diag in active_set
    if pick_cols[i].button(
        ("● " if is_active else "○ ") + diag,
        key=f"dentex_pick_{case['image_id']}_{diag}",
        type="primary" if is_active else "secondary",
        use_container_width=True,
    ):
        s = set(st.session_state[active_key])
        if diag in s and len(s) > 1:
            s.discard(diag)        # toggle off (only if at least one stays)
        else:
            s.add(diag)            # toggle on (or no-op if it's the lone selected)
        st.session_state[active_key] = sorted(s)
        st.session_state[edit_key] = False
        st.rerun()

edit_now = pick_cols[len(DIAG_LIST)].toggle(
    "✏️ Edit",
    value=st.session_state[edit_key],
    key=f"dentex_edit_toggle_{case['image_id']}",
    help="In Edit mode, click a box to select; drag to move/resize. "
         "Press Backspace/Delete to remove the selected box. "
         "Note: moving/resizing a multi-label box may reset its labels.",
)
st.session_state[edit_key] = edit_now

if pick_cols[len(DIAG_LIST) + 1].button(
    "🗑️ Clear",
    key=f"dentex_clear_{case['image_id']}",
    use_container_width=True,
):
    st.session_state[canvas_ver_key] += 1
    st.session_state[labels_key] = {}
    st.rerun()

# Stroke color: single-active → use that color; multi-active → white sentinel
if len(active_set) == 1:
    stroke_color = DIAGNOSIS_COLORS[next(iter(active_set))]
else:
    stroke_color = MULTI_STROKE
drawing_mode = "transform" if st.session_state[edit_key] else "rect"

DISPLAY_WIDTH = 900
scale = DISPLAY_WIDTH / case["width"]
canvas_height = int(case["height"] * scale)
canvas_key = f"dentex_canvas_{case['image_id']}_v{st.session_state[canvas_ver_key]}"

canvas_result = st_canvas(
    fill_color="rgba(0, 0, 0, 0)",
    stroke_width=3,
    stroke_color=stroke_color,
    background_image=pil_image,
    update_streamlit=True,
    height=canvas_height,
    width=DISPLAY_WIDTH,
    drawing_mode=drawing_mode,
    key=canvas_key,
)

# Parse drawn rectangles. Single-label boxes recover their label from stroke
# color. Multi-label boxes (white stroke) look up labels in our parallel store
# keyed by position; new ones get the current active set assigned.
color_to_diag = {v.lower(): k for k, v in DIAGNOSIS_COLORS.items()}
labels_store = st.session_state[labels_key]
new_labels_store: dict = {}
student_boxes = []
if canvas_result.json_data and isinstance(canvas_result.json_data, dict):
    for obj in canvas_result.json_data.get("objects", []):
        if obj.get("type") != "rect":
            continue
        sx = obj.get("scaleX", 1) or 1
        sy = obj.get("scaleY", 1) or 1
        disp_x = obj.get("left", 0)
        disp_y = obj.get("top", 0)
        disp_w = (obj.get("width", 0) or 0) * sx
        disp_h = (obj.get("height", 0) or 0) * sy
        pos_hash = (round(disp_x), round(disp_y), round(disp_w), round(disp_h))
        stroke = (obj.get("stroke") or "").lower()

        if stroke == MULTI_STROKE.lower():
            diagnoses = list(labels_store.get(pos_hash, ()))
            if not diagnoses:
                # New multi-label rect → adopt the current active set
                diagnoses = sorted(active_set)
        else:
            diag = color_to_diag.get(stroke)
            if not diag:
                continue
            diagnoses = [diag]

        new_labels_store[pos_hash] = tuple(diagnoses)
        student_boxes.append({
            "diagnoses": diagnoses,
            "bbox": [disp_x / scale, disp_y / scale, disp_w / scale, disp_h / scale],
        })

# Prune deleted/moved boxes from the store
st.session_state[labels_key] = new_labels_store

info_col, list_col = st.columns([1, 2])
with info_col:
    st.metric("Boxes drawn", len(student_boxes))
    active_str = " + ".join(sorted(active_set)) if active_set else "(none)"
    st.caption(f"Active: **{active_str}**")
    st.caption(f"Mode: **{'Edit' if st.session_state[edit_key] else 'Draw'}**")
with list_col:
    if student_boxes:
        with st.expander(f"Drawn boxes ({len(student_boxes)})", expanded=False):
            for i, b in enumerate(student_boxes):
                x, y, w, h = (int(v) for v in b["bbox"])
                label_str = " + ".join(b["diagnoses"])
                st.markdown(f"{i + 1}. **{label_str}** — ({x}, {y}) · {w}×{h} px")
    else:
        st.info("Draw at least one box to enable submission.")

# Diagnoses present = union of every label on every drawn box
diag_answer = sorted({d for b in student_boxes for d in b["diagnoses"]})

# ---- Diagnosis writeup form ----
with st.form(f"dentex_unified_{case['image_id']}"):
    st.markdown("**Write up your assessment:**")
    findings_answer = st.text_area(
        "Findings (describe each box's location and reasoning)",
        placeholder="e.g., Tooth 48 — impacted, horizontal orientation\n"
                    "Tooth 36 — radiolucency on mesial suggestive of caries...",
    )
    impression = st.text_area(
        "Overall impression",
        placeholder="e.g., Panoramic radiograph showing multiple carious lesions and "
                    "one impacted third molar...",
    )
    confidence = st.slider(
        "Confidence (1-5)", 1, 5, 3, key=f"dentex_unified_conf_{case['image_id']}"
    )
    submitted = st.form_submit_button("Submit for Feedback", type="primary")

unified_chat_key = f"dentex_chat_unified_{case['image_id']}"
last_eval_key = f"dentex_unified_eval_{case['image_id']}"

if submitted:
    if not student_boxes:
        st.warning("Draw at least one bounding box before submitting.")
    elif not st.session_state.get("anthropic_api_key"):
        st.warning("Anthropic API key missing — set ANTHROPIC_API_KEY in .streamlit/secrets.toml.")
    else:
        # Expand multi-label student boxes into per-label virtual boxes so the
        # existing single-label IoU/match logic can grade each label independently.
        expanded_boxes = []
        for b in student_boxes:
            for d in b["diagnoses"]:
                expanded_boxes.append({"bbox": b["bbox"], "diagnosis": d})
        report = evaluate_annotation(expanded_boxes, case["annotations"], iou_thresh=0.3)
        st.session_state[last_eval_key] = report

        findings_detail = "\n".join(
            f"  - Tooth {a['fdi_number']} ({a['quadrant']}): {a['diagnosis']}"
            for a in case["annotations"]
        )
        student_box_summary = "\n".join(
            f"  - Box {i + 1}: [{' + '.join(b['diagnoses'])}], "
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
            f"DIAGNOSES PRESENT (from box labels): "
            f"{', '.join(diag_answer) if diag_answer else 'none'}\n\n"
            f"OVERALL IMPRESSION:\n{impression or '(none)'}"
        )
        start_socratic(unified_chat_key, context, initial_msg, case["summary"])

# Persisted metrics + GT overlay (after a submit)
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

# Progress
st.divider()
if "dentex_completed" not in st.session_state:
    st.session_state["dentex_completed"] = set()
if submitted:
    st.session_state["dentex_completed"].add(case["image_id"])
completed = len(st.session_state.get("dentex_completed", set()))
st.progress(completed / len(cases), text=f"Progress: {completed}/{len(cases)} DENTEX cases attempted")
