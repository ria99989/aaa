import argparse
from pathlib import Path

from PIL import Image

from .core import composite, cutout, detect_boxes, draw_boxes

EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

ap = argparse.ArgumentParser(prog="objcut", description="背景除去 / 物体検出")
ap.add_argument("src", type=Path, help="画像ファイルまたはフォルダ")
ap.add_argument("dst", type=Path, help="出力フォルダ")
ap.add_argument("--mode", choices=["cutout", "white", "boxes"], default="cutout",
                help="cutout=透過PNG / white=白背景 / boxes=検出枠を描画")
a = ap.parse_args()
a.dst.mkdir(parents=True, exist_ok=True)
files = [a.src] if a.src.is_file() else sorted(p for p in a.src.iterdir() if p.suffix.lower() in EXTS)
for p in files:
    img = Image.open(p).convert("RGB")
    if a.mode == "boxes":
        boxes = detect_boxes(img)
        draw_boxes(img, boxes).save(a.dst / f"{p.stem}_boxes.png")
        print(f"{p.name}: {len(boxes)} 個 {boxes}")
    else:
        rgba = cutout(img)
        (composite(rgba) if a.mode == "white" else rgba).save(a.dst / f"{p.stem}_{a.mode}.png")
print(f"{len(files)} 枚処理 -> {a.dst}")
