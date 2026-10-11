import argparse
from pathlib import Path

from .engine import run

ap = argparse.ArgumentParser(prog="receipt_ocr", description="領収書画像 -> CSV")
ap.add_argument("src", type=Path, help="画像ファイルまたはフォルダ")
ap.add_argument("out", type=Path, help="出力ファイル(.xlsx または .csv)")
ap.add_argument("--rules", type=Path, help="勘定科目ルールの JSON(任意)")
ap.add_argument("--lang", default="jpn+eng")
a = ap.parse_args()
rows = run(a.src, a.out, a.lang, a.rules)
review = sum(r["needs_review"] for r in rows)
print(f"{len(rows)} 枚処理 / 要確認 {review} 枚 -> {a.out}")
