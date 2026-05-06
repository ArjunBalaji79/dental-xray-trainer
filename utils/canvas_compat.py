"""Compatibility shim for streamlit-drawable-canvas.

The canvas (still on its 0.9.x line) does ``from streamlit.elements.image
import image_to_url`` at import time, then uses the returned URL as the
``<img>`` src inside its iframe. Two problems on modern Streamlit:

1. ``streamlit.elements.image.image_to_url`` was removed in Streamlit >= 1.32
   (moved to ``streamlit.elements.lib.image_utils`` with a different signature).
2. Even when present, ``image_to_url`` returns a *relative* ``/media/...`` path
   that the canvas iframe resolves against its own component origin (a CDN),
   not the user's Streamlit app host. That works on localhost (same origin)
   but breaks on Streamlit Community Cloud — the canvas renders blank.

We sidestep both by replacing ``image_to_url`` with a function that returns a
self-contained ``data:image/png;base64,...`` URL. Origin-agnostic, version-
agnostic. Must run BEFORE ``streamlit_drawable_canvas`` is imported so the
``from ... import`` in the canvas module picks up our patched attribute.
"""

from __future__ import annotations

import base64
import io

import streamlit.elements.image as _legacy_image_module


def _to_data_url(image, *_args, **_kwargs) -> str:
    """Return a self-contained data: URL for any image input the canvas hands us."""
    if hasattr(image, "save"):  # PIL.Image
        buf = io.BytesIO()
        image.convert("RGB").save(buf, format="PNG")
        payload = buf.getvalue()
    elif isinstance(image, (bytes, bytearray)):
        payload = bytes(image)
    elif isinstance(image, str):
        return image
    else:
        try:
            from PIL import Image as _PILImage
            import numpy as _np
            arr = _np.asarray(image)
            buf = io.BytesIO()
            _PILImage.fromarray(arr).convert("RGB").save(buf, format="PNG")
            payload = buf.getvalue()
        except Exception:
            return ""
    return "data:image/png;base64," + base64.b64encode(payload).decode("ascii")


_legacy_image_module.image_to_url = _to_data_url
