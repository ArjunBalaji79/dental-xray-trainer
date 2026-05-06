"""Socratic chat helper — drives a hard-capped 3-exchange guided dialog."""

import streamlit as st

from utils.anthropic_client import (
    build_coaching_system_prompt,
    build_socratic_system_prompt,
    get_socratic_response,
)

MAX_EXCHANGES = 3


def start_socratic(chat_key: str, context: str, initial_user_msg: str, reveal_md: str = "") -> None:
    """(Re)initialize a Socratic chat for the given key with the student's submission."""
    st.session_state[chat_key] = {
        "context": context,
        "history": [{"role": "user", "content": initial_user_msg}],
        "reveal_md": reveal_md,
    }


def render_socratic(chat_key: str) -> None:
    """Render the Socratic chat for `chat_key` if it exists in session state.

    Generates the next assistant turn when the last message is from the student,
    renders the full conversation, exposes a chat input until the 3-exchange cap,
    and reveals the ground-truth answer on the final turn.
    """
    state = st.session_state.get(chat_key)
    if not state:
        return

    history = state["history"]
    context = state["context"]

    if history and history[-1]["role"] == "user":
        assistant_turn = sum(1 for m in history if m["role"] == "assistant") + 1
        sys_prompt = build_socratic_system_prompt(context, assistant_turn, MAX_EXCHANGES)
        with st.spinner("Thinking..."):
            try:
                reply = get_socratic_response(sys_prompt, history)
            except Exception as e:
                st.error(f"Error getting Socratic response: {e}")
                return
        history.append({"role": "assistant", "content": reply})

    st.subheader("Socratic Feedback")
    for msg in history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    assistant_count = sum(1 for m in history if m["role"] == "assistant")

    if assistant_count < MAX_EXCHANGES:
        remaining = MAX_EXCHANGES - assistant_count
        user_reply = st.chat_input(
            f"Your response ({remaining} exchange{'s' if remaining != 1 else ''} left)...",
            key=f"{chat_key}_input",
        )
        if user_reply:
            history.append({"role": "user", "content": user_reply})
            st.rerun()
    else:
        st.info(f"Reached the {MAX_EXCHANGES}-exchange cap.")
        if state.get("reveal_md"):
            with st.expander("See correct answers", expanded=True):
                st.markdown(state["reveal_md"])


def start_coaching(chat_key: str, context: str, initial_user_msg: str) -> None:
    """Start a no-reveal coaching chat (for mid-exercise hints)."""
    st.session_state[chat_key] = {
        "mode": "coaching",
        "context": context,
        "history": [{"role": "user", "content": initial_user_msg}],
    }


def render_coaching(chat_key: str, label: str = "AI Coach") -> None:
    """Render a coaching chat that never reveals the answer. No turn cap."""
    state = st.session_state.get(chat_key)
    if not state:
        return

    history = state["history"]
    context = state["context"]

    if history and history[-1]["role"] == "user":
        sys_prompt = build_coaching_system_prompt(context)
        with st.spinner("Thinking..."):
            try:
                reply = get_socratic_response(sys_prompt, history)
            except Exception as e:
                st.error(f"Error: {e}")
                return
        history.append({"role": "assistant", "content": reply})

    st.markdown(f"**{label}**")
    for msg in history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_reply = st.chat_input("Describe what you see...", key=f"{chat_key}_input")
    if user_reply:
        history.append({"role": "user", "content": user_reply})
        st.rerun()
