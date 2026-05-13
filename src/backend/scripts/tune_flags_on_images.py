#!/usr/bin/env python3
"""
Batch-run red/orange flag detection on images (no ROS).

Usage (from repo root, with lunar venv for OpenCV):
  PYTHONPATH=src/backend uv run --project lunar python src/backend/scripts/tune_flags_on_images.py \\
    --input field_photos/in --output field_photos/out

Or: make tune-flags input=field_photos/in output=field_photos/out
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Repo layout: .../src/backend/scripts/this_file.py
_REPO_ROOT = Path(__file__).resolve().parents[3]
_BACKEND_SRC = _REPO_ROOT / "src" / "backend"
if str(_BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(_BACKEND_SRC))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from backend.flag_detection_math import detect_red_orange_flags  # noqa: E402

_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def main() -> int:
    p = argparse.ArgumentParser(description="Run flag detector on a folder of images.")
    p.add_argument("--input", type=Path, required=True, help="Directory of images.")
    p.add_argument("--output", type=Path, required=True, help="Directory for overlays + results.jsonl.")
    p.add_argument("--horizontal-fov-deg", type=float, default=69.0)
    p.add_argument("--min-area-px", type=float, default=180.0)
    p.add_argument("--max-candidates", type=int, default=5)
    args = p.parse_args()

    in_dir = args.input.expanduser().resolve()
    out_dir = args.output.expanduser().resolve()
    if not in_dir.is_dir():
        print(f"error: input is not a directory: {in_dir}", file=sys.stderr)
        return 2
    out_dir.mkdir(parents=True, exist_ok=True)

    results_path = out_dir / "results.jsonl"
    paths = sorted(
        f
        for f in in_dir.iterdir()
        if f.is_file() and f.suffix.lower() in _EXTENSIONS
    )
    if not paths:
        print(f"error: no images found in {in_dir}", file=sys.stderr)
        return 2

    with open(results_path, "w", encoding="utf-8") as results_f:
        for img_path in paths:
            raw = img_path.read_bytes()
            frame = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
            if frame is None:
                print(f"skip (decode failed): {img_path.name}", file=sys.stderr)
                continue

            candidates = detect_red_orange_flags(
                frame,
                horizontal_fov_deg=args.horizontal_fov_deg,
                min_area_px=args.min_area_px,
                max_candidates=args.max_candidates,
            )
            h, w = frame.shape[:2]
            vis = frame.copy()
            for i, c in enumerate(candidates):
                color = (0, 255, 0) if i == 0 else (0, 200, 255)
                txt = f"#{i} brg={c.get('bearing_deg')} conf={c.get('confidence'):.2f}"
                cv2.putText(vis, txt, (8, 24 + i * 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)

            out_img = out_dir / f"{img_path.stem}_flags{img_path.suffix.lower()}"
            cv2.imwrite(str(out_img), vis)

            row = {
                "file": img_path.name,
                "width": w,
                "height": h,
                "candidate_count": len(candidates),
                "candidates": candidates,
                "params": {
                    "horizontal_fov_deg": args.horizontal_fov_deg,
                    "min_area_px": args.min_area_px,
                    "max_candidates": args.max_candidates,
                },
            }
            results_f.write(json.dumps(row) + "\n")
            print(f"ok {img_path.name} -> {out_img.name} ({len(candidates)} candidates)")

    print(f"wrote {results_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
