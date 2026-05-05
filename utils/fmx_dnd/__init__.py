"""Custom Streamlit component: drag-and-drop FMX image arranger.

State lives entirely in the iframe to avoid Streamlit-rerun flicker on every
drop. Python only receives a payload when the user clicks the in-iframe
"Check My Arrangement" button:

    {"action": "submit", "token": <unique>, "state": {"bank": [...], "rows": [[...], ...]}}

Pass a new ``reset_token`` to force the iframe to reinitialise (e.g. on shuffle).
"""

from pathlib import Path
from typing import List, Optional

import streamlit.components.v1 as components

_FRONTEND_DIR = Path(__file__).parent / "frontend"

_component_func = components.declare_component(
    "fmx_dnd",
    path=str(_FRONTEND_DIR),
)


def fmx_dnd(
    images,
    num_rows: int,
    reset_token: str = "",
    key: Optional[str] = None,
    height: int = 700,
    layout_mode: str = "default",
    row_labels: Optional[List[str]] = None,
):
    """Render the drag-and-drop arranger.

    Parameters
    ----------
    images : list of {"letter": str, "data_uri": str}
    num_rows : number of FMX rows
    reset_token : opaque string; change to force a re-init (e.g. on shuffle)
    key : Streamlit widget key
    height : iframe height hint in px (the iframe also auto-resizes)
    layout_mode : "default" (flex-wrap rows) or "fmx_standard" (3-row 7/4/7 grid
        with a bitewing center gap). Only takes effect when num_rows == 3.
    row_labels : optional list of row header strings (e.g. anatomical names).

    Returns
    -------
    None until the user submits. On submit, returns
    ``{"action": "submit", "token": ..., "state": {"bank": [...], "rows": [...]}}``.
    In FMX-standard mode the bitewing row (index 1) is emitted as a flat list
    ordered left-half then right-half (so col 0..3 maps to L0, L1, R0, R1).
    """
    return _component_func(
        images=images,
        num_rows=num_rows,
        reset_token=reset_token,
        layout_mode=layout_mode,
        row_labels=row_labels or [],
        key=key,
        default=None,
        height=height,
    )
