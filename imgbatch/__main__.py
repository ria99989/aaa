import argparse
from pathlib import Path

from .core import process_dir


def main():
    ap = argparse.ArgumentParser(prog="imgbatch", description="画像の一括処理")
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    ap.add_argument("--max-width", type=int)
    ap.add_argument("--max-height", type=int)
    ap.add_argument("--format", choices=["jpeg", "png", "webp"])
    ap.add_argument("--trim", action="store_true", help="余白を自動トリミング")
    ap.add_argument("--watermark", help="透かし文字")
    ap.add_argument("--quality", type=int, default=90)
    a = ap.parse_args()
    out = process_dir(a.src, a.dst, max_w=a.max_width, max_h=a.max_height, fmt=a.format,
                      trim=a.trim, watermark=a.watermark, quality=a.quality)
    print(f"{len(out)} 枚を処理しました -> {a.dst}")


main()
