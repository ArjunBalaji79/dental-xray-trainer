"""FMX Labeling Exercise: drag-and-drop arrangement of a full-mouth X-ray series.

Students see shuffled radiographs extracted from an FMX sheet and drag each
image into the correct row + position. After submitting, a Socratic chat
reflects on mistakes. During the exercise, an AI Coach can give non-revealing
hints.
"""

import base64
import io
import os
import random
import tempfile
from pathlib import Path

import streamlit as st
from PIL import Image

from utils.fmx_dnd import fmx_dnd
from utils.fmx_splitter import extract_from_pptx, split_composite_image
from utils.socratic_chat import (
    render_coaching,
    render_socratic,
    start_coaching,
    start_socratic,
)

st.set_page_config(page_title="FMX Labeling Exercise", page_icon="🦷", layout="wide")

st.title("FMX Labeling — Drag & Drop")
st.markdown(
    "Drag each shuffled radiograph into the correct **row and position** of the FMX layout. "
    "Top row is **maxillary**, bottom row is **mandibular**. After you submit, a Socratic "
    "tutor will help you reason about any mistakes."
)

# Sidebar
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Cerebras API Key", type="password", key="cerebras_api_key_label")
    if api_key:
        st.session_state["cerebras_api_key"] = api_key
    elif not st.session_state.get("cerebras_api_key"):
        try:
            key = st.secrets.get("CEREBRAS_API_KEY", "")
            if key:
                st.session_state["cerebras_api_key"] = key
        except Exception:
            pass

st.divider()

# --- Source: bundled PPTX or upload ---
uploaded = st.file_uploader(
    "Upload an FMX image (JPG/PNG) or PowerPoint (.pptx)",
    type=["png", "jpg", "jpeg", "pptx"],
)

bundled_pptx = Path(__file__).parent.parent / "FMX Annotated.pptx"
use_bundled = False
if not uploaded and bundled_pptx.exists():
    use_bundled = st.checkbox("Use bundled FMX file (FMX Annotated.pptx)", value=True)

if not uploaded and not use_bundled:
    st.info("Upload an FMX composite image or PowerPoint to start the exercise.")
    st.stop()


@st.cache_data(show_spinner="Extracting radiographs...")
def _load_from_pptx(pptx_bytes, _filename):
    with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
        tmp.write(pptx_bytes)
        tmp_path = tmp.name
    try:
        slides = extract_from_pptx(tmp_path)
    finally:
        os.unlink(tmp_path)
    return slides


@st.cache_data(show_spinner="Detecting radiographs...")
def _load_from_image(img_bytes):
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    return split_composite_image(img)


images = None
slide_title = ""

if uploaded:
    file_ext = uploaded.name.rsplit(".", 1)[-1].lower()
    if file_ext == "pptx":
        slides = _load_from_pptx(uploaded.read(), uploaded.name)
        if slides:
            best = max(slides, key=lambda s: len(s["images"]))
            images = best["images"]
            slide_title = best["title"]
    else:
        images = _load_from_image(uploaded.read())
elif use_bundled:
    with open(str(bundled_pptx), "rb") as f:
        slides = _load_from_pptx(f.read(), bundled_pptx.name)
    if slides:
        slides_with_images = [s for s in slides if len(s["images"]) > 1]
        if len(slides_with_images) > 1:
            with st.sidebar:
                st.divider()
                slide_names = [
                    f"Slide {s['slide_number']}: {s['title'] or '(untitled)'} — {len(s['images'])} images"
                    for s in slides_with_images
                ]
                chosen = st.selectbox("Select slide", range(len(slides_with_images)),
                                      format_func=lambda i: slide_names[i])
                images = slides_with_images[chosen]["images"]
                slide_title = slides_with_images[chosen]["title"]
        elif slides_with_images:
            images = slides_with_images[0]["images"]
            slide_title = slides_with_images[0]["title"]

if not images:
    st.error("Could not extract any radiographs from this file.")
    st.stop()

n = len(images)
num_rows = max(img["row"] for img in images) + 1

if slide_title:
    st.subheader(slide_title)
st.caption(f"**{n} radiographs** detected · **{num_rows} rows** in this layout")

# Stable shuffle, persisted per (n, slide_title)
exercise_key = f"fmx_exercise_{n}_{slide_title}"

col_reset, _ = st.columns([1, 5])
with col_reset:
    if st.button("🔀 Shuffle & Reset"):
        for k in list(st.session_state.keys()):
            if k.startswith(exercise_key) or k.startswith(f"coach_{exercise_key}") \
                    or k.startswith(f"fmx_label_chat_{exercise_key}"):
                st.session_state.pop(k, None)
        st.rerun()

if exercise_key not in st.session_state:
    order = list(range(n))
    random.shuffle(order)
    st.session_state[exercise_key] = order

shuffled_order = st.session_state[exercise_key]
shuffled_images = [images[i] for i in shuffled_order]


def _letter(idx: int) -> str:
    return chr(65 + idx) if idx < 26 else f"AA{idx - 26}"


def _to_data_uri(pil_img: Image.Image, max_px: int = 240) -> str:
    img = pil_img.copy()
    img.thumbnail((max_px, max_px))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


# Build image cards once (cached on shuffle)
cards_key = f"{exercise_key}_cards"
if cards_key not in st.session_state:
    st.session_state[cards_key] = [
        {"letter": _letter(i), "data_uri": _to_data_uri(shuffled_images[i]["image"])}
        for i in range(n)
    ]
cards = st.session_state[cards_key]

# Initial state for the DnD widget
dnd_state_key = f"{exercise_key}_dnd_state"
initial_state = st.session_state.get(dnd_state_key, None)

st.subheader("Arrange the radiographs")
arrangement = fmx_dnd(
    images=cards,
    num_rows=num_rows,
    initial_state=initial_state,
    key=f"{exercise_key}_widget",
    height=200 + num_rows * 180,
)

# Persist whatever the widget last reported (so reruns / shuffle keep their state)
if arrangement is not None:
    st.session_state[dnd_state_key] = arrangement

# Compute current state for status + scoring (widget value, fallback to stored)
current = arrangement or initial_state or {
    "bank": [c["letter"] for c in cards],
    "rows": [[] for _ in range(num_rows)],
}
bank_count = len(current.get("bank", []))

col_submit, col_status = st.columns([1, 4])
with col_submit:
    submitted = st.button("✅ Check My Arrangement", type="primary",
                          key=f"{exercise_key}_submit", disabled=(bank_count > 0))
with col_status:
    if bank_count > 0:
        st.caption(f"⚠️ {bank_count} image(s) still in **Unplaced**.")
    else:
        st.caption("All images placed. Ready to submit.")

if submitted:
    st.divider()

    # Build placement: letter -> (student_row, student_col)
    placement = {}
    for row_i, row_letters in enumerate(current["rows"]):
        for col_i, letter in enumerate(row_letters):
            placement[letter] = (row_i, col_i)

    results = []
    correct_count = 0
    for idx in range(n):
        letter = _letter(idx)
        gt = shuffled_images[idx]
        student_rc = placement.get(letter)
        gt_rc = (gt["row"], gt["col"])
        is_correct = student_rc == gt_rc
        if is_correct:
            correct_count += 1
        results.append({
            "letter": letter,
            "idx": idx,
            "student_rc": student_rc,
            "gt_rc": gt_rc,
            "gt_number": gt["number"],
            "is_correct": is_correct,
        })

    score_pct = correct_count / n * 100
    if score_pct == 100:
        st.balloons()
        st.success(f"**Perfect! {correct_count}/{n} correct (100%)**")
    elif score_pct >= 70:
        st.success(f"**Good job! {correct_count}/{n} correct ({score_pct:.0f}%)**")
    elif score_pct >= 40:
        st.warning(f"**{correct_count}/{n} correct ({score_pct:.0f}%)** — keep practicing!")
    else:
        st.error(f"**{correct_count}/{n} correct ({score_pct:.0f}%)** — review the FMX layout.")

    # Per-row breakdown
    st.subheader("Your arrangement")
    for row_i in range(num_rows):
        row_letters = current["rows"][row_i] if row_i < len(current["rows"]) else []
        st.markdown(f"**Row {row_i + 1}**")
        if not row_letters:
            st.caption("_(empty)_")
            continue
        cols = st.columns(len(row_letters))
        for col_i, letter in enumerate(row_letters):
            idx = ord(letter) - 65
            r = next(x for x in results if x["letter"] == letter)
            with cols[col_i]:
                st.image(shuffled_images[idx]["image"], use_container_width=True)
                if r["is_correct"]:
                    st.markdown(f"**{letter}** :green[✓]")
                else:
                    st.markdown(
                        f"**{letter}** :red[✗] → should be R{r['gt_rc'][0] + 1}"
                        f"C{r['gt_rc'][1] + 1} (#{r['gt_number']})"
                    )

    # Correct arrangement
    st.divider()
    st.subheader("Correct FMX Arrangement")
    sorted_images_gt = sorted(images, key=lambda x: x["number"])
    max_row = max(img["row"] for img in sorted_images_gt)
    for row_idx in range(max_row + 1):
        row_imgs = [img for img in sorted_images_gt if img["row"] == row_idx]
        row_imgs.sort(key=lambda x: x["col"])
        if not row_imgs:
            continue
        cols = st.columns(len(row_imgs))
        for col, img_data in zip(cols, row_imgs):
            with col:
                st.image(img_data["image"], use_container_width=True,
                         caption=f"#{img_data['number']}")

    # Socratic reflection on mistakes
    label_chat_key = f"fmx_label_chat_{exercise_key}"
    if st.session_state.get("cerebras_api_key"):
        wrong = [r for r in results if not r["is_correct"]]
        if wrong and label_chat_key not in st.session_state:
            mistakes_desc = "\n".join(
                f"- Image {r['letter']}: placed at "
                f"R{r['student_rc'][0] + 1}C{r['student_rc'][1] + 1}, "
                f"correct is R{r['gt_rc'][0] + 1}C{r['gt_rc'][1] + 1} (position #{r['gt_number']})"
                for r in wrong
            )
            context = (
                "Standard FMX layout:\n"
                "  Top row: Maxillary — right molars → left molars\n"
                "  Middle row(s): Bitewings / additional PAs\n"
                "  Bottom row: Mandibular — right molars → left molars\n\n"
                f"Student scored {correct_count}/{n}. Mistakes:\n{mistakes_desc}\n\n"
                "Key discriminators: maxillary vs mandibular (sinus floor, zygomatic process vs "
                "mental foramen, inferior border), anterior vs posterior (tooth morphology), "
                "left vs right (orientation dot), bitewings vs periapicals "
                "(crown-only vs crown+root view)."
            )
            initial_msg = (
                f"I scored {correct_count}/{n} on this FMX labeling exercise. "
                f"My mistakes:\n{mistakes_desc}"
            )
            start_socratic(label_chat_key, context, initial_msg)

    render_socratic(label_chat_key)

# ---- AI Coach (mid-exercise, no-reveal) ----
if st.session_state.get("cerebras_api_key"):
    st.divider()
    with st.expander("🤖 AI Coach — ask for hints while you arrange", expanded=False):
        st.caption("Pick an image, describe what you see, and the AI will ask Socratic "
                   "questions without revealing the position.")
        coach_col1, coach_col2 = st.columns([1, 3])
        with coach_col1:
            chosen_letter = st.selectbox(
                "Image",
                [_letter(i) for i in range(n)],
                key=f"{exercise_key}_coach_letter",
            )
        with coach_col2:
            initial_obs = st.text_input(
                f"What do you see in image {chosen_letter}?",
                key=f"{exercise_key}_coach_obs",
                placeholder="e.g. 'A big dark area at the top and two small teeth...'",
            )

        coach_key = f"coach_{exercise_key}_{chosen_letter}"
        if st.button("Start / Restart Coach", key=f"{exercise_key}_coach_start_{chosen_letter}"):
            if not initial_obs.strip():
                st.warning("Describe what you see first.")
            else:
                idx = ord(chosen_letter) - 65
                gt = shuffled_images[idx]
                context = (
                    f"The student is looking at image {chosen_letter} from a "
                    f"{n}-image FMX series. The correct position of this image "
                    f"is #{gt['number']} (row {gt['row'] + 1}, column {gt['col'] + 1}) "
                    "in the FMX layout. NEVER reveal this. Ask them to describe "
                    "landmarks, tooth morphology, and the dark/bright regions that "
                    "would discriminate maxillary vs mandibular, anterior vs "
                    "posterior, periapical vs bitewing."
                )
                start_coaching(coach_key, context,
                               f"I'm looking at image {chosen_letter}. {initial_obs}")
                st.rerun()

        if coach_key in st.session_state:
            idx = ord(chosen_letter) - 65
            show_col1, show_col2 = st.columns([1, 2])
            with show_col1:
                st.image(shuffled_images[idx]["image"], caption=f"Image {chosen_letter}",
                         use_container_width=True)
            with show_col2:
                render_coaching(coach_key, label=f"Coach for Image {chosen_letter}")
else:
    st.info("💡 Add a Cerebras API key in the sidebar to enable AI Coach + post-submit Socratic feedback.")
