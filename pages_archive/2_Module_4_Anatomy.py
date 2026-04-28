"""Module 4: Normal Anatomy Recognition.

Students identify anatomical structures, restorations, and
distinguish normal from abnormal findings on dental radiographs.
"""

import streamlit as st
from utils.sample_cases import MODULE_4_CASES
from utils.socratic_chat import start_socratic, render_socratic

st.set_page_config(page_title="Module 4: Anatomy Recognition", page_icon="🦷", layout="wide")

st.title("Module 4: Normal Anatomy Recognition")
st.markdown(
    "Examine the radiograph and identify all **anatomical structures**, **restorations**, "
    "and any **abnormal findings**. Then compare your assessment with AI feedback."
)

# Sidebar
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Cerebras API Key", type="password", key="cerebras_api_key_m4")
    if api_key:
        st.session_state["cerebras_api_key"] = api_key

    st.divider()

    st.header("Upload Your Own X-ray")
    uploaded = st.file_uploader("Upload a DICOM or image file", type=["dcm", "png", "jpg", "jpeg"], key="m4_upload")
    if uploaded:
        st.session_state["uploaded_file_m4"] = uploaded

    st.divider()
    case_idx = st.selectbox(
        "Select a case",
        range(len(MODULE_4_CASES)),
        format_func=lambda i: f"Case {i + 1}: {MODULE_4_CASES[i]['description'][:50]}...",
    )

case = MODULE_4_CASES[case_idx]

# Layout
col_img, col_form = st.columns([1, 1])

with col_img:
    st.subheader("Radiograph")

    if "uploaded_file_m4" in st.session_state and st.session_state["uploaded_file_m4"] is not None:
        uploaded = st.session_state["uploaded_file_m4"]
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
        st.info("Using your uploaded image. The sample case answers are shown for reference.")
    else:
        from pathlib import Path
        img_path = Path(case["image_path"])
        if img_path.exists():
            st.image(str(img_path), use_container_width=True, caption=case["description"])
        else:
            st.error(f"Sample image not found: {img_path.name}")

    # Teaching points
    with st.expander("Teaching Points"):
        for point in case["teaching_points"]:
            st.markdown(f"- {point}")

with col_form:
    st.subheader("Your Assessment")

    with st.form(f"m4_form_{case_idx}"):
        st.markdown("**1. List all anatomical structures you can identify:**")
        structures = st.text_area(
            "Structures",
            placeholder="e.g., enamel, dentin, pulp chamber, PDL space, lamina dura, alveolar bone...",
            label_visibility="collapsed",
        )

        st.markdown("**2. Are there any restorations visible?**")
        restorations = st.text_area(
            "Restorations",
            placeholder="e.g., amalgam restoration on tooth #30 mesial surface, or 'no restorations visible'",
            label_visibility="collapsed",
        )

        st.markdown("**3. Do you see anything abnormal?**")
        abnormalities = st.text_area(
            "Abnormalities",
            placeholder="e.g., radiolucency on mesial of #14 suggestive of caries, or 'no abnormalities'",
            label_visibility="collapsed",
        )

        st.markdown("**4. Overall impression:**")
        impression = st.text_area(
            "Impression",
            placeholder="e.g., Normal periapical radiograph with no pathology, or describe findings...",
            label_visibility="collapsed",
        )

        confidence = st.slider("How confident are you? (1 = guessing, 5 = certain)", 1, 5, 3, key="m4_conf")

        submitted = st.form_submit_button("Submit for Feedback", type="primary")

    chat_key = f"m4_chat_{case['id']}"

    if submitted:
        if not structures.strip() and not impression.strip():
            st.warning("Please describe at least the structures or your overall impression.")
        elif not st.session_state.get("cerebras_api_key"):
            st.warning("Please enter your Cerebras API key in the sidebar.")
        else:
            structures_list = "\n".join(f"  - {s}" for s in case["structures_present"])
            abnormalities_list = (
                "\n".join(f"  - {a}" for a in case["abnormalities"])
                if case["abnormalities"]
                else "  - None"
            )
            context = (
                f"- Image type: {case['image_type']}\n"
                f"- Structures present:\n{structures_list}\n"
                f"- Overall finding: {case['findings']}\n"
                f"- Abnormalities:\n{abnormalities_list}"
            )
            initial_msg = (
                f"Student assessment (confidence: {confidence}/5):\n\n"
                f"STRUCTURES IDENTIFIED:\n{structures}\n\n"
                f"RESTORATIONS:\n{restorations}\n\n"
                f"ABNORMALITIES:\n{abnormalities}\n\n"
                f"OVERALL IMPRESSION:\n{impression}"
            )

            reveal_lines = [
                f"**Image type:** {case['image_type']}",
                "**Structures present:**",
                *[f"- {s}" for s in case["structures_present"]],
                f"**Finding:** {case['findings']}",
            ]
            if case["abnormalities"]:
                reveal_lines.append("**Abnormalities:**")
                reveal_lines.extend(f"- {a}" for a in case["abnormalities"])
            else:
                reveal_lines.append("**Abnormalities:** None")
            reveal_md = "\n\n".join(reveal_lines)

            start_socratic(chat_key, context, initial_msg, reveal_md)

    render_socratic(chat_key)

# Progress tracker
st.divider()
if "m4_completed" not in st.session_state:
    st.session_state["m4_completed"] = set()

if submitted and (structures.strip() or impression.strip()):
    st.session_state["m4_completed"].add(case["id"])

completed = len(st.session_state.get("m4_completed", set()))
total = len(MODULE_4_CASES)
st.progress(completed / total, text=f"Progress: {completed}/{total} cases attempted")
