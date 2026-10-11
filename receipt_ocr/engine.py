from pathlib import Path

import pytesseract
from PIL import Image, ImageOps

from .category import classify, load_rules
from .export import write_csv, write_xlsx
from .parse import parse_receipt
from .preprocess import enhance

EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}


def preprocess(img: Image.Image) -> Image.Image:
    """EXIF回転 → 影除去・傾き補正・コントラスト正規化(preprocess.enhance)。"""
    return enhance(ImageOps.exif_transpose(img))


def ocr_image(path: Path, lang: str = "jpn+eng") -> str:
    return pytesseract.image_to_string(preprocess(Image.open(path)), lang=lang, config="--psm 6")


def run(src: Path, out: Path, lang: str = "jpn+eng", rules_path: Path | None = None) -> list[dict]:
    """画像 -> 行データ。出力形式は拡張子で決定(.xlsx / .csv)。"""
    rules = load_rules(rules_path)
    files = [src] if src.is_file() else sorted(p for p in src.iterdir() if p.suffix.lower() in EXTS)
    rows = []
    for p in files:
        raw = ocr_image(p, lang)
        row = {"file": p.name, **parse_receipt(raw)}
        row["category"] = classify(f"{row['store'] or ''} {raw}", rules)
        # 抽出できなかった項目がある行は目視確認フラグを立てる
        row["needs_review"] = any(row[k] is None for k in ("date", "store", "total"))
        rows.append(row)
    (write_xlsx if out.suffix.lower() == ".xlsx" else write_csv)(rows, out)
    return rows
