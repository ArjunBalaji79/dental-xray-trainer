"""Wire real DenPAR intra-oral periapical radiographs into Modules 1, 3, 5.

Reads the DenPAR dataset at ../dataset (gitignored, ~217MB), selects images that
match each case using the Characteristics spreadsheet (Arch / Site / FDI teeth
present), optimizes them into static/img/denpar/, and writes an `image` (and,
where useful, `roi`) field back into each module's cases JSON.

Module 1's technique errors don't exist in a clean dataset, so they are
synthesized from clean films (cone cut, exposure, motion, herringbone, etc.).

Run:  python wire_images.py
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import openpyxl
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DS = ROOT / "dataset"
OUT_IMG = HERE / "static" / "img" / "denpar"
SPLITS = ["Training", "Validation", "Testing"]
random.seed(7)  # deterministic selection


# ---------------------------------------------------------------------------
# index the dataset
# ---------------------------------------------------------------------------
def build_index():
    paths, kpts, bone = {}, {}, {}
    for sp in SPLITS:
        for p in (DS / sp / "Images").glob("*.jpg"):
            paths[p.stem] = p
        kp = DS / sp / "Key Points Annotations"
        if kp.exists():
            for j in kp.glob("*.json"):
                try:
                    kpts[j.stem] = json.load(open(j)).get("bboxes", [])
                except Exception:
                    pass
        bl = DS / sp / "Bone Level Annotations"
        if bl.exists():
            for j in bl.glob("*.json"):
                try:
                    bone[j.stem] = json.load(open(j)).get("Num_of_Bone_Lines", 0)
                except Exception:
                    pass
    meta = {}
    ws = openpyxl.load_workbook(DS / "Characteristics of radiographs included.xlsx",
                               data_only=True)["Sheet1"]
    for r in list(ws.iter_rows(values_only=True))[1:]:
        if r[0] is None:
            continue
        iid = str(int(float(r[0])))
        fdi = [x.strip() for x in str(r[3]).split(",")] if r[3] else []
        fdi = [x for x in fdi if x.isdigit()]
        meta[iid] = {"arch": (r[1] or "").strip(), "site": (r[2] or "").strip(), "fdi": fdi}
    return paths, kpts, bone, meta


PATHS, KPTS, BONE, META = build_index()


def candidates(arch=None, site=None, fdi=None, min_bone=None):
    out = []
    for iid, m in META.items():
        if iid not in PATHS:
            continue
        if arch and m["arch"].lower() != arch.lower():
            continue
        if site and m["site"].lower() != site.lower():
            continue
        if fdi and fdi not in m["fdi"]:
            continue
        if min_bone and BONE.get(iid, 0) < min_bone:
            continue
        out.append(iid)
    out.sort(key=lambda i: int(i))
    return out


def optimize(iid, dest_name, width=900, transform=None):
    im = Image.open(PATHS[iid]).convert("L")
    if transform:
        im = transform(im)
    if im.width > width:
        im = im.resize((width, int(im.height * width / im.width)), Image.LANCZOS)
    im = im.convert("RGB")
    OUT_IMG.mkdir(parents=True, exist_ok=True)
    im.save(OUT_IMG / dest_name, quality=82)
    return dest_name


def roi_for(iid, prefer="largest"):
    """Approximate ROI (percent) from the tooth bboxes — illustrative marker."""
    bxs = KPTS.get(iid) or []
    if not bxs:
        return None
    im = Image.open(PATHS[iid])
    W, H = im.size
    if prefer == "largest":
        b = max(bxs, key=lambda z: (z[2] - z[0]) * (z[3] - z[1]))
    elif prefer == "center":
        b = min(bxs, key=lambda z: abs((z[0] + z[2]) / 2 - W / 2))
    else:
        b = bxs[0]
    cx, cy = (b[0] + b[2]) / 2 / W * 100, (b[1] + b[3]) / 2 / H * 100
    r = max(b[2] - b[0], b[3] - b[1]) / 2 / W * 100 * 1.15
    return {"x": round(cx, 1), "y": round(cy, 1), "r": round(min(r, 22), 1)}


def pick(arch=None, site=None, fdi=None, min_bone=None, used=None):
    used = used or set()
    for relax in range(3):
        cands = candidates(arch, site if relax < 1 else None, fdi if relax < 2 else None, min_bone)
        cands = [c for c in cands if c not in used]
        if cands:
            iid = cands[len(cands) // 3]  # stable, not always the first
            used.add(iid)
            return iid
    return None


# ---------------------------------------------------------------------------
# Module 3 — tooth identification (Universal -> FDI, arch, site)
# ---------------------------------------------------------------------------
M3_MAP = {
    "M3-01": ("36", "Lower", "Left", "largest"),
    "M3-02": ("16", "Upper", "Right", "largest"),
    "M3-03": ("13", "Upper", "Right", "center"),
    "M3-04": ("44", "Lower", "Right", "center"),
    "M3-05": ("38", "Lower", "Left", "largest"),
    "M3-06": ("26", "Upper", "Left", "largest"),
}


def wire_module3(used):
    f = HERE / "data" / "module3_cases.json"
    data = json.load(open(f))
    for c in data["cases"]:
        fdi, arch, site, prefer = M3_MAP[c["id"]]
        iid = pick(arch, site, fdi, used=used)
        if not iid:
            continue
        c["image"] = "denpar/" + optimize(iid, f"m3_{c['id']}.jpg")
        c["roi"] = roi_for(iid, prefer)
    json.dump(data, open(f, "w"), indent=2, ensure_ascii=False)
    print("M3:", [(c["id"], c.get("image")) for c in data["cases"]])


# ---------------------------------------------------------------------------
# Module 5 — interpretation (findings). Area is user-clicked, no ROI needed.
# ---------------------------------------------------------------------------
M5_MAP = {
    "M5-01": ("46", "Lower", "Right", None),   # interproximal caries #30
    "M5-02": ("36", "Lower", "Left", None),    # recurrent caries #19
    "M5-03": (None, "Lower", None, 3),         # bone loss -> image with many bone lines
    "M5-04": ("46", "Lower", "Right", None),   # distal caries #30
    "M5-05": ("44", "Lower", "Right", None),   # mental foramen near premolar apex #29
}


def wire_module5(used):
    f = HERE / "data" / "module5_cases.json"
    data = json.load(open(f))
    for c in data["cases"]:
        fdi, arch, site, minbone = M5_MAP[c["id"]]
        iid = pick(arch, site, fdi, min_bone=minbone, used=used)
        if not iid:
            continue
        c["image"] = "denpar/" + optimize(iid, f"m5_{c['id']}.jpg")
    json.dump(data, open(f, "w"), indent=2, ensure_ascii=False)
    print("M5:", [(c["id"], c.get("image")) for c in data["cases"]])


# ---------------------------------------------------------------------------
# Module 1 — synthesize technique errors from clean films
# ---------------------------------------------------------------------------
def t_conecut(im):
    im = im.copy()
    d = ImageDraw.Draw(im)
    W, H = im.size
    d.polygon([(0, 0), (int(W * 0.42), 0), (0, int(H * 0.5))], fill=0)  # black corner wedge
    return im

def t_overlap(im):
    base = im.convert("L")
    shifted = ImageChops_offset(base, int(base.width * 0.03))
    return Image.blend(base, shifted, 0.5)

def ImageChops_offset(im, dx):
    from PIL import ImageChops
    return ImageChops.offset(im, dx, 0)

def t_elongate(im):
    W, H = im.size
    im2 = im.resize((W, int(H * 1.35)), Image.LANCZOS)
    top = (im2.height - H) // 2
    return im2.crop((0, top, W, top + H))

def t_foreshorten(im):
    W, H = im.size
    im2 = im.resize((W, int(H * 0.7)), Image.LANCZOS)
    canvas = Image.new("L", (W, H), 0)
    canvas.paste(im2, (0, (H - im2.height) // 2))
    return canvas

def t_motion(im):
    return im.filter(ImageFilter.GaussianBlur(radius=3.2))

def t_light(im):  # underexposure -> washed out / bright
    im = ImageEnhance.Brightness(im).enhance(1.9)
    return ImageEnhance.Contrast(im).enhance(0.55)

def t_dark(im):   # overexposure -> too dark
    return ImageEnhance.Brightness(im).enhance(0.4)

def t_herringbone(im):
    im = ImageEnhance.Brightness(im).enhance(1.4)
    W, H = im.size
    ov = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(ov)
    step = 22
    for i in range(-H, W, step):
        d.line([(i, 0), (i + H, H)], fill=90, width=3)
        d.line([(i + H, 0), (i, H)], fill=90, width=3)
    return ImageChops_screen(im, ov)

def ImageChops_screen(a, b):
    from PIL import ImageChops
    return ImageChops.screen(a, b)

M1_TRANSFORMS = {
    "M1-02": t_overlap, "M1-03": t_elongate, "M1-04": t_foreshorten, "M1-05": t_motion,
    "M1-06": t_light, "M1-07": t_dark, "M1-08": t_herringbone, "M1-09": t_conecut,
    "M1-10": t_overlap,
}


def wire_module1(used):
    f = HERE / "data" / "module1_cases.json"
    data = json.load(open(f))
    # a pool of clean posterior films for variety
    pool = candidates(arch="Lower") + candidates(arch="Upper")
    pool = [p for p in pool if p not in used]
    for i, c in enumerate(data["cases"]):
        tf = M1_TRANSFORMS.get(c["id"])
        if not tf:
            continue
        iid = pool[(i * 7) % len(pool)]
        used.add(iid)
        c["image"] = "denpar/" + optimize(iid, f"m1_{c['id']}.jpg", transform=tf)
    json.dump(data, open(f, "w"), indent=2, ensure_ascii=False)
    print("M1:", [(c["id"], c.get("image")) for c in data["cases"]])


def main():
    used = set()
    wire_module3(used)
    wire_module5(used)
    wire_module1(used)
    n = len(list(OUT_IMG.glob("*.jpg")))
    total = sum(f.stat().st_size for f in OUT_IMG.glob("*.jpg"))
    print(f"\nWrote {n} images to static/img/denpar/  ({total/1024:.0f} KB)")


if __name__ == "__main__":
    main()
