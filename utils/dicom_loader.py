"""DICOM file loading and conversion utilities."""

import io
import numpy as np
from PIL import Image

try:
    import pydicom
    HAS_PYDICOM = True
except ImportError:
    HAS_PYDICOM = False


def dicom_to_image(dicom_bytes: bytes) -> Image.Image:
    """Convert DICOM file bytes to a PIL Image."""
    if not HAS_PYDICOM:
        raise ImportError("pydicom is required to load DICOM files. Install with: pip install pydicom")

    ds = pydicom.dcmread(io.BytesIO(dicom_bytes))
    pixel_array = ds.pixel_array.astype(float)

    # Normalize to 0-255
    if pixel_array.max() != pixel_array.min():
        pixel_array = (pixel_array - pixel_array.min()) / (pixel_array.max() - pixel_array.min()) * 255.0
    pixel_array = pixel_array.astype(np.uint8)

    return Image.fromarray(pixel_array)
