"""Load FMX18 DICOM datasets from the local folder structure.

Expected layout:
  FMX18/
    1/  (patient 1, ~18 images)
    2/  (patient 2)
    3/  (patient 3)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Union

import pydicom
import numpy as np
from PIL import Image

FMX_ROOT = Path(__file__).parent.parent / "FMX18"


def _dcm_to_pil(path: Union[str, Path]) -> Image.Image:
    """Read a DICOM file and return a PIL Image."""
    ds = pydicom.dcmread(str(path))
    arr = ds.pixel_array.astype(float)
    if arr.max() != arr.min():
        arr = (arr - arr.min()) / (arr.max() - arr.min()) * 255.0
    return Image.fromarray(arr.astype(np.uint8))


def get_patients() -> list[str]:
    """Return sorted list of patient folder names."""
    if not FMX_ROOT.exists():
        return []
    return sorted(
        d for d in os.listdir(FMX_ROOT)
        if (FMX_ROOT / d).is_dir() and not d.startswith(".")
    )


def get_patient_images(patient_id: str) -> list[dict]:
    """Return list of {filename, path, image} for a patient."""
    patient_dir = FMX_ROOT / patient_id
    if not patient_dir.exists():
        return []

    images = []
    for f in sorted(os.listdir(patient_dir)):
        if f.upper().endswith(".DCM"):
            fpath = patient_dir / f
            try:
                img = _dcm_to_pil(fpath)
                images.append({
                    "filename": f,
                    "path": str(fpath),
                    "image": img,
                })
            except Exception:
                continue
    return images
