"""背景除去・物体検出のデモ用に、ダミーの商品画像と正解マスクを生成する。"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def make(seed: int = 0, size=(640, 480), n_objects: int = 1):
    rng = np.random.default_rng(seed)
    # 木目風の模様+ノイズの背景(単色ではない)
    x = np.linspace(0, 1, size[0])[None, :]
    y = np.linspace(0, 1, size[1])[:, None]
    base = 170 + 25 * np.sin(18 * x + 4 * y) + rng.normal(0, 6, (size[1], size[0]))
    bg = np.stack([base, base * 0.88, base * 0.7], -1).clip(0, 255).astype(np.uint8)
    img = Image.fromarray(bg)
    gt = Image.new("L", size, 0)
    shapes = [((90, 120, 300, 360), (200, 40, 50)), ((360, 170, 570, 340), (30, 90, 180))]
    for box, col in shapes[:n_objects]:
        for target, fill in ((img, col), (gt, 255)):
            d = ImageDraw.Draw(target)
            d.ellipse(box, fill=fill)
        d = ImageDraw.Draw(img)
        x0, y0, x1, y1 = box
        d.ellipse((x0 + 30, y0 + 25, x0 + 100, y0 + 70), fill=tuple(min(255, c + 70) for c in col))  # ハイライト
    return img.filter(ImageFilter.GaussianBlur(0.8)), gt


if __name__ == "__main__":
    out = Path(__file__).parent
    make(1, n_objects=1)[0].save(out / "object1.png")
    make(2, n_objects=2)[0].save(out / "objects2.png")
