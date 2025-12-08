#!/usr/bin/env python3
"""
Bulk watermarking tool for comic/manga pages.

Features:
- Apply a PNG watermark onto many JPG/PNG pages.
- Control anchor, offsets, margin, scale, and opacity.
- Optional per-file overrides and "avoid zones" to keep watermarks off speech bubbles.
"""

import argparse
import json
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from PIL import Image

Anchor = str
Box = Tuple[int, int, int, int]

ANCHORS: Dict[str, str] = {
    "top-left": "top-left",
    "top-right": "top-right",
    "bottom-left": "bottom-left",
    "bottom-right": "bottom-right",
    "center": "center",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add a PNG watermark onto one or many comic pages.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-w", "--watermark", type=Path, required=True, help="PNG watermark with transparency.")
    parser.add_argument("-i", "--input", type=Path, required=True, help="Folder containing input pages.")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Folder to write watermarked pages.")
    parser.add_argument(
        "--extensions",
        nargs="+",
        default=[".jpg", ".jpeg", ".png"],
        help="File extensions to process.",
    )
    parser.add_argument(
        "--recursive",
        dest="recursive",
        action="store_true",
        help="Scan input subfolders (e.g., chapters) recursively.",
    )
    parser.add_argument(
        "--no-recursive",
        dest="recursive",
        action="store_false",
        help="Disable recursive scan; only process files directly in input folder.",
    )
    parser.set_defaults(recursive=True)
    parser.add_argument(
        "--anchor",
        choices=list(ANCHORS.keys()),
        default="bottom-right",
        help="Base anchor position for the watermark.",
    )
    parser.add_argument("--offset-x", type=int, default=0, help="Horizontal pixel offset applied after anchoring.")
    parser.add_argument("--offset-y", type=int, default=0, help="Vertical pixel offset applied after anchoring.")
    parser.add_argument("--margin", type=int, default=16, help="Margin in pixels from the anchored edge.")
    parser.add_argument(
        "--scale",
        type=float,
        default=0.25,
        help="Watermark width as a fraction of the page width (height preserves aspect).",
    )
    parser.add_argument(
        "--opacity",
        type=float,
        default=0.6,
        help="Opacity multiplier for the watermark alpha channel (0-1).",
    )
    parser.add_argument("--quality", type=int, default=92, help="JPEG quality for output.")
    parser.add_argument(
        "--format",
        choices=["jpeg", "png", "keep"],
        default="jpeg",
        help='Output format. "keep" matches the input file extension.',
    )
    parser.add_argument("--suffix", default="", help="Suffix inserted before file extension in output filenames.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite outputs if they already exist.")
    parser.add_argument("--dry-run", action="store_true", help="Compute positions but do not write files.")
    parser.add_argument("--sample", type=int, help="Process only the first N files (after sorting).")
    parser.add_argument(
        "--avoid-json",
        type=Path,
        help=(
            "JSON with per-file overrides/avoid zones. Keys can be '*' (global), filename, or filename with extension. "
            'Example: {"page01.jpg": {"avoid": [[50,60,120,80]], "anchor": "top-left", "offset": [10, 12]}}'
        ),
    )
    return parser.parse_args()


def iter_pages(folder: Path, extensions: Iterable[str], recursive: bool = True) -> List[Path]:
    if not folder.is_dir():
        raise SystemExit(f"Input folder not found: {folder}")
    ext_set = set()
    for ext in extensions:
        ext_set.add(ext.lower() if ext.startswith(".") else f".{ext.lower()}")
    if recursive:
        candidates = folder.rglob("*")
    else:
        candidates = folder.iterdir()
    paths = [p for p in candidates if p.is_file() and p.suffix.lower() in ext_set]
    return sorted(paths, key=lambda p: str(p).lower())


def load_overrides(path: Optional[Path]) -> Dict[str, dict]:
    if not path:
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("Overrides JSON must be an object mapping filenames to settings.")
    return data


def merge_overrides(name: str, overrides: Dict[str, dict]) -> dict:
    merged: Dict[str, object] = {}
    for key in ("*", name, name.lower()):
        if key in overrides and isinstance(overrides[key], dict):
            merged.update(overrides[key])
    return merged


def resize_watermark(base: Image.Image, page_w: int, page_h: int, scale: float) -> Image.Image:
    scale = max(0.01, min(scale, 1.0))
    target_w = max(1, int(page_w * scale))
    ratio = target_w / base.width
    target_h = max(1, int(base.height * ratio))
    return base.resize((target_w, target_h), Image.LANCZOS)


def apply_opacity(watermark: Image.Image, opacity: float) -> Image.Image:
    opacity = max(0.0, min(opacity, 1.0))
    if opacity >= 0.999:
        return watermark
    wm = watermark.copy()
    alpha = wm.getchannel("A").point(lambda a: int(a * opacity))
    wm.putalpha(alpha)
    return wm


def anchor_position(anchor: Anchor, page_w: int, page_h: int, wm_w: int, wm_h: int, margin: int) -> Tuple[int, int]:
    if anchor == "top-left":
        return margin, margin
    if anchor == "top-right":
        return page_w - wm_w - margin, margin
    if anchor == "bottom-left":
        return margin, page_h - wm_h - margin
    if anchor == "bottom-right":
        return page_w - wm_w - margin, page_h - wm_h - margin
    if anchor == "center":
        return (page_w - wm_w) // 2, (page_h - wm_h) // 2
    raise ValueError(f"Unknown anchor: {anchor}")


def boxes_intersect(a: Box, b: Box) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay)


def fits_inside(x: int, y: int, w: int, h: int, page_w: int, page_h: int, avoid: List[Box]) -> bool:
    if x < 0 or y < 0 or x + w > page_w or y + h > page_h:
        return False
    for zone in avoid:
        if len(zone) != 4:
            continue
        if boxes_intersect((x, y, w, h), (int(zone[0]), int(zone[1]), int(zone[2]), int(zone[3]))):
            return False
    return True


def pick_position(
    primary_anchor: Anchor,
    page_size: Tuple[int, int],
    wm_size: Tuple[int, int],
    margin: int,
    offset_x: int,
    offset_y: int,
    avoid: List[Box],
) -> Tuple[int, int, Anchor, bool]:
    page_w, page_h = page_size
    wm_w, wm_h = wm_size
    ordered = []
    for candidate in [primary_anchor, "bottom-right", "bottom-left", "top-right", "top-left", "center"]:
        if candidate not in ordered:
            ordered.append(candidate)

    for anchor in ordered:
        base_x, base_y = anchor_position(anchor, page_w, page_h, wm_w, wm_h, margin)
        x, y = base_x + offset_x, base_y + offset_y
        if fits_inside(x, y, wm_w, wm_h, page_w, page_h, avoid):
            return x, y, anchor, True

    # Fall back to the requested anchor even if it overlaps avoid zones so work always proceeds.
    base_x, base_y = anchor_position(primary_anchor, page_w, page_h, wm_w, wm_h, margin)
    return base_x + offset_x, base_y + offset_y, primary_anchor, False


def output_path_for(src: Path, input_root: Path, output_dir: Path, suffix: str, fmt: str) -> Path:
    try:
        rel = src.relative_to(input_root)
    except ValueError:
        rel = Path(src.name)
    if not isinstance(rel, Path):
        rel = Path(rel)
    stem = rel.stem + suffix
    target_ext = rel.suffix if fmt == "keep" else (".png" if fmt == "png" else ".jpg")
    target_dir = output_dir / rel.parent
    return target_dir / f"{stem}{target_ext}"


def compose_watermarked_image(
    page_path: Path,
    watermark_base: Image.Image,
    args: argparse.Namespace,
    overrides: Dict[str, dict],
) -> Tuple[Image.Image, str]:
    page = Image.open(page_path)
    page_rgb = page.convert("RGB")
    page_w, page_h = page_rgb.size

    merged = merge_overrides(page_path.name, overrides)
    anchor = merged.get("anchor", args.anchor)
    offset = merged.get("offset", [args.offset_x, args.offset_y])
    offset_x = int(offset[0]) if isinstance(offset, (list, tuple)) and len(offset) >= 1 else args.offset_x
    offset_y = int(offset[1]) if isinstance(offset, (list, tuple)) and len(offset) >= 2 else args.offset_y
    margin = int(merged.get("margin", args.margin))
    scale = float(merged.get("scale", args.scale))
    opacity = float(merged.get("opacity", args.opacity))
    avoid_zones = merged.get("avoid", [])
    avoid: List[Box] = []
    if isinstance(avoid_zones, list):
        for zone in avoid_zones:
            if isinstance(zone, (list, tuple)) and len(zone) == 4:
                avoid.append((int(zone[0]), int(zone[1]), int(zone[2]), int(zone[3])))

    wm_resized = resize_watermark(watermark_base, page_w, page_h, scale)
    wm_ready = apply_opacity(wm_resized, opacity)
    pos_x, pos_y, chosen_anchor, obeyed_avoid = pick_position(
        anchor, (page_w, page_h), wm_ready.size, margin, offset_x, offset_y, avoid
    )

    canvas = page_rgb.copy()
    canvas.paste(wm_ready, (pos_x, pos_y), wm_ready)
    info = (
        f"{page_path.name}: anchor={chosen_anchor} pos=({pos_x},{pos_y}) size={wm_ready.size} "
        f"avoid_ok={obeyed_avoid} avoid_zones={len(avoid)}"
    )
    return canvas, info


def process_file(
    page_path: Path,
    watermark_base: Image.Image,
    args: argparse.Namespace,
    overrides: Dict[str, dict],
    input_root: Path,
    log: Callable[[str], None] = print,
) -> None:
    canvas, info = compose_watermarked_image(page_path, watermark_base, args, overrides)
    if args.dry_run:
        log(f"[dry-run] {info}")
        return

    output_dir = args.output
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_path_for(page_path, input_root, output_dir, args.suffix, args.format)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists() and not args.overwrite:
        log(f"[skip exists] {out_path.name}")
        return

    save_kwargs = {}
    if out_path.suffix.lower() in {".jpg", ".jpeg"}:
        save_kwargs.update(dict(quality=args.quality, subsampling=0, optimize=True))
        out_format = "JPEG"
    elif out_path.suffix.lower() == ".png":
        out_format = "PNG"
    else:
        out_format = None
    canvas.save(out_path, format=out_format, **save_kwargs)
    log(f"[wrote] {out_path} :: {info}")


def run_with_args(args: argparse.Namespace, log: Callable[[str], None] = print, limit_dir: Optional[Path] = None) -> None:
    overrides = load_overrides(args.avoid_json)

    watermark_path = args.watermark
    if not watermark_path.is_file():
        raise SystemExit(f"Watermark file not found: {watermark_path}")
    watermark = Image.open(watermark_path).convert("RGBA")

    pages = iter_pages(args.input, args.extensions, recursive=args.recursive)
    if limit_dir:
        resolved = limit_dir.resolve()
        filtered = []
        for p in pages:
            rp = p.resolve()
            if str(rp).startswith(str(resolved)):
                filtered.append(p)
        pages = filtered
    if args.sample:
        pages = pages[: args.sample]
    if not pages:
        raise SystemExit("No matching pages found.")

    for page_path in pages:
        process_file(page_path, watermark, args, overrides, args.input, log=log)


def main() -> None:
    args = parse_args()
    run_with_args(args, log=print)


if __name__ == "__main__":
    main()
