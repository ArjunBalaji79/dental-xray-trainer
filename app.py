"""Dental X-ray Training Platform — MVP

An AI-powered educational tool for dental radiology training.
Built with Streamlit + Cerebras API.

Three focused modules:
  1. Tooth ID & Image Orientation
  2. Pathology Practice (DENTEX, expert-labeled)
  3. FMX Labeling — drag & drop arrangement
"""

import streamlit as st

st.set_page_config(
    page_title="Dental X-ray Training Platform",
    page_icon="🦷",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🦷 Dental X-ray Training Platform")
st.markdown("### AI-Powered Radiology Education — Socratic, Image-Grounded, Expert-Labeled")

st.divider()

# Auto-load API key from secrets if available
if not st.session_state.get("cerebras_api_key"):
    try:
        key = st.secrets.get("CEREBRAS_API_KEY", "")
        if key:
            st.session_state["cerebras_api_key"] = key
    except Exception:
        pass

with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Cerebras API Key", type="password", key="cerebras_api_key_home")
    if api_key:
        st.session_state["cerebras_api_key"] = api_key
    if st.session_state.get("cerebras_api_key"):
        st.success("API key set")
    else:
        st.warning("Enter your Cerebras API key to enable AI feedback")

# Three module cards
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        """
        ### 1️⃣ Tooth ID & Orientation

        **Learn to identify:**
        - Bitewing vs periapical vs panoramic
        - Maxillary vs mandibular arch
        - Anterior vs posterior regions
        - Individual tooth numbers

        Sample cases with **Socratic AI feedback**.

        👈 Open **Tooth ID** in the sidebar.
        """
    )

with col2:
    st.markdown(
        """
        ### 2️⃣ Pathology Practice (DENTEX)

        **50 panoramic radiographs** from the DENTEX dataset (MICCAI 2023)
        with **expert-verified ground truth**:
        - Tooth-level bounding boxes & FDI numbers
        - Caries, Deep Caries, Periapical Lesion, Impacted

        AI feedback grounded in real expert labels — **not hallucinated**.

        👈 Open **Pathology DENTEX** in the sidebar.
        """
    )

with col3:
    st.markdown(
        """
        ### 3️⃣ FMX Labeling — Drag & Drop

        Real full-mouth X-ray series, **shuffled**.
        **Drag each radiograph** into the correct row and position.

        - Native HTML5 drag-and-drop
        - **AI Coach** during the exercise (no spoilers)
        - Socratic reflection after submitting

        👈 Open **FMX Labeling** in the sidebar.
        """
    )

st.divider()

st.markdown(
    """
    ### How It Works

    1. **Practice** on real, expert-labeled radiographs
    2. **Submit** your answer (or arrangement)
    3. **Reason** with a Socratic AI tutor — it asks questions before revealing answers
    4. **Learn** from grounded, image-specific feedback

    ---

    *Built for the Dr. Perelman AIxEducation Project. Powered by Cerebras inference.*
    """
)
