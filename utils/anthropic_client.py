"""Anthropic Claude API client.

Mirrors the function signatures of the previous Gemini client so call sites
in ``utils/socratic_chat.py`` need only an import swap. Default model is
Haiku 4.5 — fast, cheap, and strong enough for Socratic dental tutoring.
"""

import streamlit as st
from anthropic import Anthropic

DEFAULT_MODEL = "claude-haiku-4-5"


def get_client() -> Anthropic:
    """Return a configured Anthropic client (raises Streamlit error if no key)."""
    api_key = st.session_state.get("anthropic_api_key", "")
    if not api_key:
        try:
            api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
        except Exception:
            api_key = ""
        if api_key:
            st.session_state["anthropic_api_key"] = api_key
    if not api_key:
        st.error(
            "Anthropic API key missing — set ANTHROPIC_API_KEY in "
            ".streamlit/secrets.toml."
        )
        st.stop()
    return Anthropic(api_key=api_key)


def get_feedback(system_prompt: str, user_message: str, model: str = DEFAULT_MODEL) -> str:
    """Single-shot completion."""
    client = get_client()
    msg = client.messages.create(
        model=model,
        max_tokens=1024,
        temperature=0.3,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    return msg.content[0].text


def build_socratic_system_prompt(context: str, turn: int, max_turns: int = 3) -> str:
    """Build a turn-aware Socratic system prompt.

    Turns 1..max_turns-1 probe without revealing; the final turn reveals the answer.
    """
    if turn < max_turns:
        stage = (
            f"You are on exchange {turn} of {max_turns}. "
            "DO NOT reveal, hint at, confirm, or deny the correct answer yet. "
            "Ask ONE probing follow-up question that makes the student justify or reconsider "
            "what they just said. Anchor the question in their own words (HOW did they conclude, "
            "WHY that feature, WHAT landmark would confirm it). "
            "Keep it to 2-3 short sentences. End with exactly one question mark."
        )
    else:
        stage = (
            f"This is the FINAL exchange ({turn} of {max_turns}). NOW reveal the answer. "
            "For each part of the student's original submission, state CORRECT or INCORRECT, "
            "explain the reasoning using what they said in prior turns, and end with one "
            "clearly labeled KEY TAKEAWAY. Be encouraging but precise. Use dental terminology."
        )
    return (
        "You are the AI Companion, a dental radiology instructor. You guide students to the answer "
        "through targeted questioning — you never give the answer directly until the final "
        "exchange. You have the ground truth below; use it privately to judge their thinking.\n\n"
        f"GROUND TRUTH (keep hidden until the final exchange):\n{context}\n\n"
        f"{stage}"
    )


def get_socratic_response(
    system_prompt: str,
    history: list,
    model: str = DEFAULT_MODEL,
) -> str:
    """Multi-turn Socratic response.

    ``history`` is a list of ``{"role": "user"|"assistant", "content": str}``
    in the OpenAI shape used by ``utils/socratic_chat.py``. Anthropic accepts
    the same shape directly (system prompt is a top-level kwarg, not a message).
    """
    client = get_client()
    msg = client.messages.create(
        model=model,
        max_tokens=800,
        temperature=0.4,
        system=system_prompt,
        messages=history,
    )
    return msg.content[0].text


def build_coaching_system_prompt(context: str) -> str:
    """No-reveal coaching prompt — for in-exercise hints."""
    return (
        "You are the AI Companion, a dental radiology coach helping a student DURING a labeling "
        "exercise. You must NEVER reveal the correct position, number, or answer — "
        "not now, not ever in this chat. Your goal is to make the student observe and "
        "reason about anatomical features (maxillary sinus floor, zygomatic process, "
        "nasal fossa, mental foramen, inferior mandibular border, genial tubercles, "
        "crown morphology, bitewing crown-only view vs PA crown-and-root view, "
        "orientation dots). Ask ONE focused question per reply. Keep replies 2-3 short "
        "sentences. End with a question mark. If the student tries to pressure you into "
        "revealing, redirect: ask them what feature they see instead.\n\n"
        f"GROUND TRUTH (use privately to guide questioning, NEVER reveal):\n{context}"
    )
