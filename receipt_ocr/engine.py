import csv
from pathlib import Path

import pytesseract
from PIL import Image, ImageOps

from .parse import parse_receipt

EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}


def preprocess(img: Image.Image) -> Image.Image:
    """グレースケール化・コントラスト補正・小さい画像の拡大で認識率を上げる。"""
    img = ImageOps.exif_transpose(img).convert("L")
    img = ImageOps.autocontrast(img)
    if img.width < 1200:
        s = 1200 / img.width
        img = img.resize((1200, round(img.height * s)), Image.LANCZOS)
    return img


def ocr_image(path: Path, lang: str = "jpn+eng") -> str:
    return pytesseract.image_to_string(preprocess(Image.open(path)), lang=lang, config="--psm 6")


def run(src: Path, out_csv: Path, lang: str = "jpn+eng") -> list[dict]:
    files = [src] if src.is_file() else sorted(p for p in src.iterdir() if p.suffix.lower() in EXTS)
    rows = []
    for p in files:
        row = {"file": p.name, **parse_receipt(ocr_image(p, lang))}
        # 抽出できなかった項目がある行は目視確認フラグを立てる
        row["needs_review"] = any(row[k] is None for k in ("date", "store", "total"))
        rows.append(row)
    with out_csv.open("w", newline="", encoding="utf-8-sig") as f:  # Excel で文字化けしない
        w = csv.DictWriter(f, fieldnames=["file", "date", "store", "total", "needs_review"])
        w.writeheader()
        w.writerows(rows)
    return rows
