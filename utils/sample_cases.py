"""Sample dental X-ray cases for the training modules.

Uses local images from:
  - sample_images/   (periapical/bitewing images converted from FMX18 DICOMs)
  - datasets/dentex/ (panoramic radiographs from the DENTEX dataset)
"""

from pathlib import Path

_SAMPLE_DIR = Path(__file__).parent.parent / "sample_images"
_DENTEX_DIR = (
    Path(__file__).parent.parent
    / "datasets"
    / "dentex"
    / "validation_data"
    / "quadrant_enumeration_disease"
    / "xrays"
)

# --- Module 1: Tooth Identification & Image Orientation ---

MODULE_1_CASES = [
    {
        "id": "m1_001",
        "image_path": str(_SAMPLE_DIR / "fmx_sample_1.png"),
        "image_type": "Bitewing",
        "region": "Posterior",
        "arch": "Both maxillary and mandibular",
        "teeth_visible": "Premolars and molars — crowns of upper and lower posterior teeth",
        "description": "Bitewing radiograph showing posterior teeth crowns.",
        "hints": [
            "Bitewings show the crowns of both upper and lower teeth on the same film.",
            "They are ideal for detecting interproximal caries.",
            "You cannot see the root apices on a bitewing.",
        ],
    },
    {
        "id": "m1_002",
        "image_path": str(_DENTEX_DIR / "val_0.png"),
        "image_type": "Panoramic (OPG)",
        "region": "Full mouth",
        "arch": "Both maxillary and mandibular",
        "teeth_visible": "All teeth visible — full dentition overview",
        "description": "Panoramic radiograph (orthopantomogram) showing full dentition.",
        "hints": [
            "Panoramic images show all teeth in a single curved image.",
            "The mandibular canal is visible as a dark band in the lower jaw.",
            "Note the bilateral symmetry of the image.",
        ],
    },
    {
        "id": "m1_003",
        "image_path": str(_SAMPLE_DIR / "fmx_sample_2.png"),
        "image_type": "Periapical (PA)",
        "region": "Posterior",
        "arch": "Maxillary (upper)",
        "teeth_visible": "Upper posterior region with dental implant visible",
        "description": "Periapical radiograph of maxillary posterior region with implant.",
        "hints": [
            "Look at the root-to-crown ratio — PAs show the full tooth including the root apex.",
            "The roots point upward in maxillary teeth.",
            "A dental implant appears as a threaded radiopaque screw.",
        ],
    },
    {
        "id": "m1_004",
        "image_path": str(_SAMPLE_DIR / "fmx_sample_4.png"),
        "image_type": "Periapical (PA)",
        "region": "Anterior",
        "arch": "Mandibular (lower)",
        "teeth_visible": "Lower anterior teeth — incisors and canines",
        "description": "Periapical radiograph of mandibular anterior region.",
        "hints": [
            "Roots point downward in mandibular teeth.",
            "Lower anterior teeth have single, thin roots.",
            "The mental foramen may be visible near the premolar area.",
        ],
    },
]

# --- Module 4: Normal Anatomy Recognition ---

MODULE_4_CASES = [
    {
        "id": "m4_001",
        "image_path": str(_SAMPLE_DIR / "fmx_sample_3.png"),
        "image_type": "Periapical",
        "structures_present": [
            "Enamel (bright white outer layer of crown)",
            "Dentin (slightly less radiopaque layer under enamel)",
            "Pulp chamber (dark area in center of tooth)",
            "Periodontal ligament space (thin dark line around roots)",
            "Lamina dura (white line surrounding PDL space)",
            "Alveolar bone (supporting bone around teeth)",
            "Maxillary sinus floor (radiopaque line above root apices)",
        ],
        "findings": "Normal anatomy — no pathology detected",
        "abnormalities": [],
        "description": "Periapical radiograph of maxillary posterior region showing normal anatomy.",
        "teaching_points": [
            "Enamel is the most radiopaque (whitest) structure in the mouth.",
            "The PDL space should be uniform in width around the root.",
            "An intact lamina dura suggests healthy periodontal attachment.",
        ],
    },
    {
        "id": "m4_002",
        "image_path": str(_SAMPLE_DIR / "fmx_sample_1.png"),
        "image_type": "Bitewing",
        "structures_present": [
            "Enamel",
            "Dentin",
            "Pulp chambers",
            "Alveolar crest (bone between teeth)",
        ],
        "findings": "Normal bitewing — evaluate for interproximal caries",
        "abnormalities": [],
        "description": "Bitewing showing posterior teeth for anatomy identification.",
        "teaching_points": [
            "Bitewings are the best view for detecting interproximal caries.",
            "Compare restoration margins to the tooth structure for gaps.",
            "Alveolar crests should be 1-2mm below the CEJ in healthy bone levels.",
        ],
    },
    {
        "id": "m4_003",
        "image_path": str(_DENTEX_DIR / "val_0.png"),
        "image_type": "Panoramic",
        "structures_present": [
            "Maxillary sinuses (dark areas above upper teeth)",
            "Mandibular canal (dark band in lower jaw)",
            "Mental foramen (small dark circle near premolars)",
            "Nasal septum (midline structure)",
            "Condyles (TMJ)",
            "Hyoid bone (U-shaped bone below mandible)",
        ],
        "findings": "Panoramic anatomy — identify landmarks",
        "abnormalities": [],
        "description": "Panoramic radiograph for anatomical landmark identification.",
        "teaching_points": [
            "The maxillary sinuses can mimic pathology — know their normal appearance.",
            "The mandibular canal carries the inferior alveolar nerve — critical for extractions.",
            "Ghost images (artifacts) are common on panoramics — don't mistake them for pathology.",
        ],
    },
    {
        "id": "m4_004",
        "image_path": str(_SAMPLE_DIR / "fmx_sample_2.png"),
        "image_type": "Periapical",
        "structures_present": [
            "Dental implant (threaded radiopaque fixture)",
            "Implant crown/abutment",
            "Alveolar bone surrounding implant",
            "Adjacent natural tooth structures",
        ],
        "findings": "Dental implant visible with surrounding anatomy",
        "abnormalities": [],
        "description": "Periapical radiograph showing a dental implant and surrounding structures.",
        "teaching_points": [
            "Implants appear as highly radiopaque threaded screws.",
            "Evaluate bone-implant contact — radiolucency around an implant may indicate failure.",
            "Compare the implant to adjacent natural tooth anatomy.",
        ],
    },
]
