"""Load and parse the DENTEX validation dataset.

DENTEX provides panoramic dental X-rays with COCO-style annotations
containing three hierarchical labels per annotation:
  - category_id_1: FDI quadrant (0→Q1 upper-right, 1→Q2 upper-left, 2→Q3 lower-left, 3→Q4 lower-right)
  - category_id_2: tooth position within quadrant (0→1 through 7→8)
  - category_id_3: diagnosis (0→Impacted, 1→Caries, 2→Periapical Lesion, 3→Deep Caries)

FDI tooth number = quadrant_name * 10 + tooth_position
  e.g., quadrant "4" + position "8" → FDI 48
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from PIL import Image, ImageDraw, ImageFont

DATASET_ROOT = Path(__file__).parent.parent / "datasets" / "dentex"
ANNOTATIONS_FILE = DATASET_ROOT / "validation_triple.json"
IMAGES_DIR = DATASET_ROOT / "validation_data" / "quadrant_enumeration_disease" / "xrays"

QUADRANT_NAMES = {0: "1", 1: "2", 2: "3", 3: "4"}
QUADRANT_DESCRIPTIONS = {
    0: "Upper Right (Q1)",
    1: "Upper Left (Q2)",
    2: "Lower Left (Q3)",
    3: "Lower Right (Q4)",
}
TOOTH_POSITIONS = {i: str(i + 1) for i in range(8)}
DIAGNOSES = {0: "Impacted", 1: "Caries", 2: "Periapical Lesion", 3: "Deep Caries"}

# Colors for drawing bounding boxes by diagnosis
DIAGNOSIS_COLORS = {
    "Impacted": "#FF6B6B",
    "Caries": "#FFD93D",
    "Periapical Lesion": "#6BCB77",
    "Deep Caries": "#FF8800",
}


def _load_annotations() -> dict:
    """Load the DENTEX annotation JSON."""
    if not ANNOTATIONS_FILE.exists():
        return {"images": [], "annotations": []}
    with open(ANNOTATIONS_FILE) as f:
        return json.load(f)


def fdi_number(cat_id_1: int, cat_id_2: int) -> str:
    """Convert DENTEX category IDs to FDI tooth number string."""
    quadrant = QUADRANT_NAMES[cat_id_1]
    position = TOOTH_POSITIONS[cat_id_2]
    return f"{quadrant}{position}"


def get_dentex_cases() -> list[dict]:
    """Load all DENTEX validation cases with parsed annotations.

    Returns list of dicts:
    {
        "image_id": int,
        "file_name": str,
        "image_path": Path,
        "width": int,
        "height": int,
        "annotations": [
            {
                "fdi_number": str,     # e.g. "48"
                "quadrant": str,       # e.g. "Upper Right (Q1)"
                "diagnosis": str,      # e.g. "Impacted"
                "bbox": [x, y, w, h],
            }
        ],
        "teeth_present": list[str],    # unique FDI numbers
        "diagnoses_present": list[str], # unique diagnoses
        "summary": str,                # human-readable summary
    }
    """
    data = _load_annotations()
    if not data["images"]:
        return []

    # Build lookup: image_id -> list of annotations
    ann_by_image = {}
    for ann in data["annotations"]:
        img_id = ann["image_id"]
        ann_by_image.setdefault(img_id, []).append(ann)

    cases = []
    for img_info in data["images"]:
        img_id = img_info["id"]
        file_name = img_info["file_name"]
        image_path = IMAGES_DIR / file_name

        annotations = []
        for ann in ann_by_image.get(img_id, []):
            fdi = fdi_number(ann["category_id_1"], ann["category_id_2"])
            diag = DIAGNOSES.get(ann["category_id_3"], "Unknown")
            quad_desc = QUADRANT_DESCRIPTIONS.get(ann["category_id_1"], "Unknown")
            annotations.append({
                "fdi_number": fdi,
                "quadrant": quad_desc,
                "diagnosis": diag,
                "bbox": ann["bbox"],
            })

        teeth = sorted(set(a["fdi_number"] for a in annotations))
        diagnoses = sorted(set(a["diagnosis"] for a in annotations))

        # Build summary
        findings = []
        for ann in annotations:
            findings.append(f"Tooth {ann['fdi_number']} ({ann['quadrant']}): {ann['diagnosis']}")

        summary = f"Panoramic radiograph with {len(annotations)} annotated finding(s).\n"
        if findings:
            summary += "Findings:\n" + "\n".join(f"  - {f}" for f in findings)
        else:
            summary += "No annotated pathology."

        cases.append({
            "image_id": img_id,
            "file_name": file_name,
            "image_path": image_path,
            "width": img_info["width"],
            "height": img_info["height"],
            "annotations": annotations,
            "teeth_present": teeth,
            "diagnoses_present": diagnoses,
            "summary": summary,
        })

    return cases


def draw_annotations(image: Image.Image, annotations: list[dict], show_labels: bool = True) -> Image.Image:
    """Draw bounding boxes and labels on a copy of the image."""
    img = image.copy().convert("RGB")
    draw = ImageDraw.Draw(img)

    for ann in annotations:
        x, y, w, h = ann["bbox"]
        color = DIAGNOSIS_COLORS.get(ann["diagnosis"], "#FFFFFF")

        # Draw box
        draw.rectangle([x, y, x + w, y + h], outline=color, width=3)

        if show_labels:
            label = f"#{ann['fdi_number']} {ann['diagnosis']}"
            # Background rectangle for text
            text_bbox = draw.textbbox((x, y - 18), label)
            draw.rectangle(text_bbox, fill=color)
            draw.text((x, y - 18), label, fill="black")

    return img
