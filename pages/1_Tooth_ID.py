"""Module 1: Tooth Identification & Image Orientation.

Students are shown a dental radiograph and asked to identify:
- Image type (bitewing, periapical, panoramic)
- Arch (maxillary, mandibular, or both)
- Region (anterior, posterior, full mouth)
- Teeth visible

The LLM evaluates their answers and provides educational feedback.
"""

import streamlit as st
from utils.sample_cases import MODULE_1_CASES
from utils.socratic_chat import start_socratic, render_socratic

st.set_page_config(page_title="Module 1: Tooth ID & Orientation", page_icon="🦷", layout="wide")

st.title("Module 1: Tooth Identification & Image Orientation")
st.markdown(
    "Identify the **image type**, **arch**, **region**, and **teeth** shown in each radiograph. "
    "Submit your answers to receive AI-powered feedback."
)

# Sidebar — API key and case selection
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Anthropic API Key", type="password", key="anthropic_api_key_m1")
    if api_key:
        st.session_state["anthropic_api_key"] = api_key

    st.divider()

    # DICOM upload
    st.header("Upload Your Own X-ray")
    uploaded = st.file_uploader("Upload a DICOM or image file", type=["dcm", "png", "jpg", "jpeg"])
    if uploaded:
        st.session_state["uploaded_file"] = uploaded

    st.divider()
    case_idx = st.selectbox(
        "Select a case",
        range(len(MODULE_1_CASES)),
        format_func=lambda i: f"Case {i + 1}: {MODULE_1_CASES[i]['description'][:50]}...",
    )

case = MODULE_1_CASES[case_idx]

# Display image
col_img, col_form = st.columns([1, 1])

with col_img:
    st.subheader("Radiograph")

    # Check for uploaded file first
    if "uploaded_file" in st.session_state and st.session_state["uploaded_file"] is not None:
        uploaded = st.session_state["uploaded_file"]
        if uploaded.name.lower().endswith(".dcm"):
            try:
                from utils.dicom_loader import dicom_to_image
                img = dicom_to_image(uploaded.read())
                uploaded.seek(0)
                st.image(img, use_container_width=True, caption="Your uploaded DICOM")
            except Exception as e:
                st.error(f"Could not load DICOM: {e}")
        else:
            try:
                st.image(uploaded, use_container_width=True, caption="Your uploaded image")
            except Exception:
                st.error("Could not display this file. Supported formats: DICOM (.dcm), PNG, JPG.")
        st.info("Using your uploaded image. Answers below refer to the sample case for comparison.")
    else:
        from pathlib import Path
        img_path = Path(case["image_path"])
        if img_path.exists():
            st.image(str(img_path), use_container_width=True, caption=case["description"])
        else:
            st.error(f"Sample image not found: {img_path.name}")

    # Hints expander
    with st.expander("Hints"):
        for hint in case["hints"]:
            st.markdown(f"- {hint}")

with col_form:
    st.subheader("Your Assessment")

    with st.form(f"m1_form_{case_idx}"):
        image_type = st.selectbox(
            "What type of radiograph is this?",
            ["-- Select --", "Bitewing", "Periapical (PA)", "Panoramic (OPG)", "Occlusal", "CBCT"],
        )
        arch = st.selectbox(
            "Which arch is shown?",
            ["-- Select --", "Maxillary (upper)", "Mandibular (lower)", "Both maxillary and mandibular"],
        )
        region = st.selectbox(
            "What region?",
            ["-- Select --", "Anterior", "Posterior", "Full mouth"],
        )
        teeth_id = st.text_area(
            "Which teeth can you identify? (use tooth numbers or descriptions)",
            placeholder="e.g., teeth 3, 4, 5 — upper right molars and premolars",
        )
        confidence = st.slider("How confident are you? (1 = guessing, 5 = certain)", 1, 5, 3)

        submitted = st.form_submit_button("Submit for Feedback", type="primary")

    chat_key = f"m1_chat_{case['id']}"

    if submitted:
        if image_type == "-- Select --" or arch == "-- Select --" or region == "-- Select --":
            st.warning("Please fill in all fields before submitting.")
        elif not st.session_state.get("anthropic_api_key"):
            st.warning("Please enter your Anthropic API key in the sidebar.")
        else:
            context = (
                f"- Image type: {case['image_type']}\n"
                f"- Arch: {case['arch']}\n"
                f"- Region: {case['region']}\n"
                f"- Teeth visible: {case['teeth_visible']}"
            )
            initial_msg = (
                f"Student submission (confidence: {confidence}/5):\n"
                f"- Image type: {image_type}\n"
                f"- Arch: {arch}\n"
                f"- Region: {region}\n"
                f"- Teeth identified: {teeth_id}"
            )
            reveal_md = (
                f"**Image type:** {case['image_type']}\n\n"
                f"**Arch:** {case['arch']}\n\n"
                f"**Region:** {case['region']}\n\n"
                f"**Teeth visible:** {case['teeth_visible']}"
            )
            start_socratic(chat_key, context, initial_msg, reveal_md)

    render_socratic(chat_key)

# Progress tracker
st.divider()
if "m1_completed" not in st.session_state:
    st.session_state["m1_completed"] = set()

if submitted and image_type != "-- Select --":
    st.session_state["m1_completed"].add(case["id"])

completed = len(st.session_state.get("m1_completed", set()))
total = len(MODULE_1_CASES)
st.progress(completed / total, text=f"Progress: {completed}/{total} cases attempted")
