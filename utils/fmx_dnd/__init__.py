"""Custom Streamlit component: drag-and-drop FMX image arranger.

The Python wrapper passes a list of (letter, base64 PNG) image cards plus the
number of rows. The frontend renders the images as draggable cards across an
"Unplaced" pool and N row containers. Each drop posts the new arrangement
({"bank": [...], "rows": [[...], ...]}) back to Python.
"""

from pathlib import Path

import streamlit.components.v1 as components

_FRONTEND_DIR = Path(__file__).parent / "frontend"

_component_func = components.declare_component(
    "fmx_dnd",
    path=str(_FRONTEND_DIR),
)


def fmx_dnd(images, num_rows: int, key: str | None = None,
            initial_state: dict | None = None, height: int = 700):
    """Render the drag-and-drop arranger.

    Parameters
    ----------
    images : list of {"letter": str, "data_uri": str}
    num_rows : int — number of FMX rows
    key : Streamlit widget key
    initial_state : optional dict {"bank": [...], "rows": [[...], ...]}
    height : iframe height in px

    Returns
    -------
    dict {"bank": [...], "rows": [[...], ...]} or None on first render.
    """
    return _component_func(
        images=images,
        num_rows=num_rows,
        initial_state=initial_state,
        key=key,
        default=None,
        height=height,
    )
