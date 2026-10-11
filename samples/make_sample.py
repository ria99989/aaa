"""デモ用のダミーレシート画像を生成する(実在の店舗・個人情報は含まない)。"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf"


def make(path, lines):
    font = ImageFont.truetype(FONT, 34)
    img = Image.new("RGB", (700, 60 + 52 * len(lines)), "white")
    d = ImageDraw.Draw(img)
    for i, t in enumerate(lines):
        d.text((40, 30 + 52 * i), t, font=font, fill="black")
    img.save(path)


if __name__ == "__main__":
    out = Path(__file__).parent
    make(out / "receipt1.png", ["サンプル商店", "領収書", "2025年3月14日", "コーヒー豆   ¥1,200",
                               "文房具セット   ¥980", "小計   ¥2,180", "合計   ¥2,180"])
    make(out / "receipt2.png", ["デモ書店 渋谷店", "2025/11/02", "技術書   ¥3,520", "雑誌   ¥1,100",
                               "合計   ¥4,620"])
