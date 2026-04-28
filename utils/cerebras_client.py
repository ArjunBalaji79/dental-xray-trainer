"""Cerebras API client using OpenAI-compatible interface."""

import streamlit as st
from openai import OpenAI


def get_client() -> OpenAI:
    """Get a Cerebras API client."""
    api_key = st.session_state.get("cerebras_api_key", "")
    if not api_key:
        # Try loading from Streamlit secrets
        api_key = st.secrets.get("CEREBRAS_API_KEY", "")
        if api_key:
            st.session_state["cerebras_api_key"] = api_key
    if not api_key:
        st.error("Please enter your Cerebras API key in the sidebar.")
        st.stop()
    return OpenAI(
        base_url="https://api.cerebras.ai/v1",
        api_key=api_key,
    )


def get_feedback(system_prompt: str, user_message: str, model: str = "qwen-3-235b-a22b-instruct-2507") -> str:
    """Get LLM feedback from Cerebras (single-shot)."""
    client = get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.3,
        max_tokens=1024,
    )
    return response.choices[0].message.content


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
        "You are a Socratic dental radiology instructor. You guide students to the answer "
        "through targeted questioning — you never give the answer directly until the final "
        "exchange. You have the ground truth below; use it privately to judge their thinking.\n\n"
        f"GROUND TRUTH (keep hidden until the final exchange):\n{context}\n\n"
        f"{stage}"
    )


def get_socratic_response(
    system_prompt: str,
    history: list,
    model: str = "qwen-3-235b-a22b-instruct-2507",
) -> str:
    """Multi-turn Socratic response. `history` is a list of {role, content} messages."""
    client = get_client()
    messages = [{"role": "system", "content": system_prompt}] + history
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.4,
        max_tokens=800,
    )
    return response.choices[0].message.content


def build_coaching_system_prompt(context: str) -> str:
    """Build a coaching prompt that NEVER reveals the answer — for in-exercise hints."""
    return (
        "You are a Socratic dental radiology coach helping a student DURING a labeling "
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
