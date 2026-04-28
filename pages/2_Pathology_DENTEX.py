"""DENTEX Practice: Panoramic X-rays with real ground-truth annotations.

Uses the DENTEX dataset (MICCAI 2023) — 50 panoramic radiographs with
tooth-level bounding boxes, FDI numbering, and pathology labels
(Caries, Deep Caries, Periapical Lesion, Impacted).
"""

import streamlit as st
from PIL import Image
from utils.dentex_loader import get_dentex_cases, draw_annotations, DIAGNOSES
from utils.socratic_chat import start_socratic, render_socratic

st.set_page_config(page_title="DENTEX Practice", page_icon="🦷", layout="wide")

st.title("DENTEX Practice — Panoramic X-rays with Ground Truth")
st.markdown(
    "Practice on **real panoramic radiographs** from the DENTEX dataset (MICCAI 2023). "
    "Each image has expert-verified **tooth-level annotations** with FDI numbering and pathology labels."
)

# Sidebar
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Cerebras API Key", type="password", key="cerebras_api_key_dentex")
    if api_key:
        st.session_state["cerebras_api_key"] = api_key
    elif not st.session_state.get("cerebras_api_key"):
        try:
            key = st.secrets.get("CEREBRAS_API_KEY", "")
            if key:
                st.session_state["cerebras_api_key"] = key
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
    st.divider()
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

col_img, col_form = st.columns([3, 2])

with col_img:
    # Toggle annotations overlay
    show_annotations = st.checkbox("Show ground truth annotations", value=False, key="show_ann")

    if show_annotations:
        annotated_img = draw_annotations(pil_image, case["annotations"])
        st.image(annotated_img, use_container_width=True, caption="With annotations")

        # Legend
        st.markdown("**Legend:**")
        legend_cols = st.columns(4)
        colors = {"Impacted": "🔴", "Caries": "🟡", "Periapical Lesion": "🟢", "Deep Caries": "🟠"}
        for i, (diag, emoji) in enumerate(colors.items()):
            legend_cols[i].markdown(f"{emoji} {diag}")
    else:
        st.image(pil_image, use_container_width=True, caption="Unannotated panoramic radiograph")

with col_form:
    # Practice mode selector
    mode = st.radio(
        "Practice mode",
        ["Tooth Identification (Module 1)", "Pathology Detection (Module 4)"],
        horizontal=True,
    )

    if mode == "Tooth Identification (Module 1)":
        with st.form("dentex_m1"):
            st.markdown("**Identify teeth with pathology in this panoramic radiograph:**")
            teeth_answer = st.text_area(
                "Which teeth do you see findings on? (use FDI numbers)",
                placeholder="e.g., 18, 28, 38, 48 (third molars), or 36, 46 (first molars)...",
            )
            quadrants = st.multiselect(
                "Which quadrants have findings?",
                ["Q1 — Upper Right", "Q2 — Upper Left", "Q3 — Lower Left", "Q4 — Lower Right"],
            )
            confidence = st.slider("Confidence (1-5)", 1, 5, 3, key="dentex_m1_conf")
            submitted = st.form_submit_button("Submit for Feedback", type="primary")

        dentex_m1_chat_key = f"dentex_chat_m1_{case['image_id']}"

        if submitted and teeth_answer.strip():
            if not st.session_state.get("cerebras_api_key"):
                st.warning("Please set your Cerebras API key.")
            else:
                correct_teeth = ", ".join(case["teeth_present"])
                correct_quads = ", ".join(sorted(set(
                    a["quadrant"] for a in case["annotations"]
                )))
                findings_detail = "\n".join(
                    f"  - Tooth {a['fdi_number']} ({a['quadrant']}): {a['diagnosis']}"
                    for a in case["annotations"]
                )
                context = (
                    f"Expert-verified panoramic radiograph ground truth (FDI numbering):\n"
                    f"- Teeth with findings: {correct_teeth}\n"
                    f"- Quadrants involved: {correct_quads}\n"
                    f"- Detailed findings:\n{findings_detail}"
                )
                initial_msg = (
                    f"Student submission (confidence: {confidence}/5):\n"
                    f"- Teeth identified: {teeth_answer}\n"
                    f"- Quadrants selected: {', '.join(quadrants) if quadrants else 'none selected'}"
                )
                start_socratic(dentex_m1_chat_key, context, initial_msg, case["summary"])

        render_socratic(dentex_m1_chat_key)

    else:  # Pathology Detection
        with st.form("dentex_m4"):
            st.markdown("**Describe all pathological findings you see:**")
            findings_answer = st.text_area(
                "Findings",
                placeholder="e.g., Tooth 48 — impacted, horizontal orientation\nTooth 36 — radiolucency on mesial suggestive of caries...",
            )
            st.markdown("**What diagnoses would you assign?**")
            diag_answer = st.multiselect(
                "Diagnoses present",
                ["Caries", "Deep Caries", "Periapical Lesion", "Impacted", "Bone Loss", "Other"],
                key="dentex_diag_select",
            )
            impression = st.text_area(
                "Overall impression",
                placeholder="e.g., Panoramic radiograph showing multiple carious lesions and one impacted third molar...",
            )
            confidence = st.slider("Confidence (1-5)", 1, 5, 3, key="dentex_m4_conf")
            submitted = st.form_submit_button("Submit for Feedback", type="primary")

        dentex_m4_chat_key = f"dentex_chat_m4_{case['image_id']}"

        if submitted and (findings_answer.strip() or impression.strip()):
            if not st.session_state.get("cerebras_api_key"):
                st.warning("Please set your Cerebras API key.")
            else:
                findings_detail = "\n".join(
                    f"  - Tooth {a['fdi_number']} ({a['quadrant']}): {a['diagnosis']}"
                    for a in case["annotations"]
                )
                correct_diags = ", ".join(case["diagnoses_present"])
                context = (
                    f"Expert-verified panoramic radiograph ground truth "
                    f"({len(case['annotations'])} findings):\n{findings_detail}\n"
                    f"Diagnoses present: {correct_diags}\n"
                    f"Use FDI numbering. Caries vs deep caries, impacted teeth, and periapical "
                    f"lesions are all distinct categories to evaluate."
                )
                initial_msg = (
                    f"Student submission (confidence: {confidence}/5):\n\n"
                    f"FINDINGS:\n{findings_answer}\n\n"
                    f"DIAGNOSES SELECTED: {', '.join(diag_answer) if diag_answer else 'none'}\n\n"
                    f"OVERALL IMPRESSION:\n{impression}"
                )
                start_socratic(dentex_m4_chat_key, context, initial_msg, case["summary"])

        render_socratic(dentex_m4_chat_key)

# Progress
st.divider()
if "dentex_completed" not in st.session_state:
    st.session_state["dentex_completed"] = set()
if submitted:
    st.session_state["dentex_completed"].add(case["image_id"])
completed = len(st.session_state.get("dentex_completed", set()))
st.progress(completed / len(cases), text=f"Progress: {completed}/{len(cases)} DENTEX cases attempted")
