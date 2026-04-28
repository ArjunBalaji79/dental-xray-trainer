"""FMX Practice: Browse and practice with real FMX18 DICOM datasets.

Students browse real patient FMX sets, view individual periapical images,
and practice both tooth identification (Module 1) and anatomy recognition (Module 4).
"""

import streamlit as st
from utils.fmx_loader import get_patients, get_patient_images
from utils.socratic_chat import start_socratic, render_socratic

st.set_page_config(page_title="FMX Practice", page_icon="🦷", layout="wide")

st.title("FMX Practice — Real Patient Cases")
st.markdown(
    "Browse full-mouth X-ray (FMX) series from real patients. "
    "Select an image and practice your identification and anatomy skills."
)

# Sidebar — API key
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Cerebras API Key", type="password", key="cerebras_api_key_fmx")
    if api_key:
        st.session_state["cerebras_api_key"] = api_key
    elif not st.session_state.get("cerebras_api_key"):
        try:
            key = st.secrets.get("CEREBRAS_API_KEY", "")
            if key:
                st.session_state["cerebras_api_key"] = key
        except Exception:
            pass

# Load patients
patients = get_patients()
if not patients:
    st.error("No FMX18 data found. Make sure the `FMX18/` folder exists with patient subfolders.")
    st.stop()

# Patient selector
with st.sidebar:
    st.divider()
    patient_id = st.selectbox("Select Patient", patients, format_func=lambda p: f"Patient {p}")

images = get_patient_images(patient_id)
if not images:
    st.warning(f"No DICOM images found for Patient {patient_id}.")
    st.stop()

# Thumbnail grid
st.subheader(f"Patient {patient_id} — {len(images)} images")

# Show thumbnails in a grid for selection
cols_per_row = 6
selected_idx = st.session_state.get("fmx_selected_idx", 0)

rows = (len(images) + cols_per_row - 1) // cols_per_row
for row in range(rows):
    cols = st.columns(cols_per_row)
    for col_i in range(cols_per_row):
        idx = row * cols_per_row + col_i
        if idx < len(images):
            with cols[col_i]:
                st.image(images[idx]["image"], use_container_width=True, caption=f"#{idx + 1}")
                if st.button(f"Select", key=f"sel_{idx}"):
                    st.session_state["fmx_selected_idx"] = idx
                    st.rerun()

st.divider()

# Selected image — detailed view and practice
sel = st.session_state.get("fmx_selected_idx", 0)
if sel >= len(images):
    sel = 0

img_data = images[sel]

st.subheader(f"Image #{sel + 1}: {img_data['filename']}")

col_img, col_form = st.columns([1, 1])

with col_img:
    st.image(img_data["image"], use_container_width=True, caption=f"Patient {patient_id} — Image #{sel + 1}")

with col_form:
    # Combined practice form (Module 1 + Module 4 questions)
    practice_mode = st.radio(
        "Practice mode",
        ["Tooth ID & Orientation (Module 1)", "Anatomy Recognition (Module 4)"],
        horizontal=True,
    )

    if practice_mode == "Tooth ID & Orientation (Module 1)":
        with st.form("fmx_m1_form"):
            image_type = st.selectbox(
                "Radiograph type?",
                ["-- Select --", "Bitewing", "Periapical (PA)", "Panoramic (OPG)", "Occlusal"],
            )
            arch = st.selectbox(
                "Which arch?",
                ["-- Select --", "Maxillary (upper)", "Mandibular (lower)", "Both"],
            )
            region = st.selectbox(
                "Region?",
                ["-- Select --", "Anterior", "Posterior (premolars)", "Posterior (molars)", "Full mouth"],
            )
            teeth_id = st.text_area(
                "Which teeth can you identify? (tooth numbers or descriptions)",
                placeholder="e.g., #18, #19, #20 — lower left molars and premolar",
            )
            submitted = st.form_submit_button("Get AI Feedback", type="primary")

        fmx_m1_chat_key = f"fmx_chat_m1_{patient_id}_{sel}"

        if submitted and image_type != "-- Select --":
            if not st.session_state.get("cerebras_api_key"):
                st.warning("Please set your Cerebras API key.")
            else:
                context = (
                    "This is an intraoral periapical (PA) radiograph from an FMX18 series. "
                    "No per-image ground truth is available; evaluate CONSISTENCY and REASONING: "
                    "is the student's combination of image type / arch / region / teeth internally "
                    "consistent, and are the tooth numbers plausible for an FMX PA view?"
                )
                initial_msg = (
                    f"Student submission:\n"
                    f"- Image type: {image_type}\n"
                    f"- Arch: {arch}\n"
                    f"- Region: {region}\n"
                    f"- Teeth identified: {teeth_id}"
                )
                start_socratic(fmx_m1_chat_key, context, initial_msg)

        render_socratic(fmx_m1_chat_key)

    else:  # Anatomy Recognition
        with st.form("fmx_m4_form"):
            structures = st.text_area(
                "Anatomical structures you can identify:",
                placeholder="e.g., enamel, dentin, pulp chambers, PDL space, lamina dura, alveolar bone...",
            )
            restorations = st.text_area(
                "Any restorations or dental materials?",
                placeholder="e.g., amalgam on #30 MO, composite on #12 DL, or 'none visible'",
            )
            abnormalities = st.text_area(
                "Any abnormal findings?",
                placeholder="e.g., periapical radiolucency at #19, widened PDL at #14, or 'none'",
            )
            impression = st.text_area(
                "Overall impression:",
                placeholder="e.g., normal periapical radiograph, or describe pathology...",
            )
            submitted = st.form_submit_button("Get AI Feedback", type="primary")

        fmx_m4_chat_key = f"fmx_chat_m4_{patient_id}_{sel}"

        if submitted and (structures.strip() or impression.strip()):
            if not st.session_state.get("cerebras_api_key"):
                st.warning("Please set your Cerebras API key.")
            else:
                context = (
                    "This is an intraoral periapical radiograph from an FMX series. "
                    "Expected structures on a PA view include: enamel, dentin, pulp, PDL space, "
                    "lamina dura, alveolar bone, cortical bone. Evaluate COMPLETENESS of structures, "
                    "plausibility of restorations described, terminology used for abnormalities, "
                    "and whether the overall impression is consistent with the findings."
                )
                initial_msg = (
                    f"Student assessment:\n\n"
                    f"STRUCTURES: {structures}\n\n"
                    f"RESTORATIONS: {restorations}\n\n"
                    f"ABNORMALITIES: {abnormalities}\n\n"
                    f"IMPRESSION: {impression}"
                )
                start_socratic(fmx_m4_chat_key, context, initial_msg)

        render_socratic(fmx_m4_chat_key)

# Progress
st.divider()
if "fmx_completed" not in st.session_state:
    st.session_state["fmx_completed"] = set()
key = f"{patient_id}_{sel}"
if submitted:
    st.session_state["fmx_completed"].add(key)
completed = len(st.session_state.get("fmx_completed", set()))
total_all = sum(len(get_patient_images(p)) for p in patients)
st.progress(min(completed / max(total_all, 1), 1.0), text=f"FMX images practiced: {completed}/{total_all}")
