"""Compatibility shim for streamlit-drawable-canvas on Streamlit >= 1.32.

The canvas package (still on its 0.9.x line) calls
``streamlit.elements.image.image_to_url`` — a private helper that Streamlit
moved to ``streamlit.elements.lib.image_utils`` and changed the signature of
(``width: int`` → ``layout_config: LayoutConfig``).

Importing this module before ``streamlit_drawable_canvas`` patches the old
attribute back onto ``streamlit.elements.image`` so the canvas keeps working.
"""

from __future__ import annotations

import streamlit.elements.image as _legacy_image_module

if not hasattr(_legacy_image_module, "image_to_url"):
    from streamlit.elements.lib.image_utils import image_to_url as _new_image_to_url
    from streamlit.elements.lib.layout_utils import LayoutConfig as _LayoutConfig

    def image_to_url(image, width, clamp, channels, output_format, image_id):
        """Old-signature wrapper that delegates to the modern image_to_url."""
        return _new_image_to_url(
            image,
            _LayoutConfig(width=width),
            clamp,
            channels,
            output_format,
            image_id,
        )

    _legacy_image_module.image_to_url = image_to_url
