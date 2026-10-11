from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageOps

EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}


def resize_fit(img: Image.Image, max_w: int | None, max_h: int | None) -> Image.Image:
    """アスペクト比を保ったまま (max_w, max_h) に収める。拡大はしない。"""
    w, h = img.size
    scale = min((max_w or w) / w, (max_h or h) / h, 1.0)
    if scale >= 1.0:
        return img
    return img.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)


def trim_border(img: Image.Image, tolerance: int = 10) -> Image.Image:
    """四隅の色と近い余白を切り落とす。"""
    rgb = img.convert("RGB")
    bg = Image.new("RGB", rgb.size, rgb.getpixel((0, 0)))
    diff = ImageChops.difference(rgb, bg).convert("L").point(lambda p: 255 if p > tolerance else 0)
    bbox = diff.getbbox()
    return img.crop(bbox) if bbox else img


def add_watermark(img: Image.Image, text: str, opacity: int = 128) -> Image.Image:
    """右下に半透明テキストを入れる。"""
    base = img.convert("RGBA")
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    x0, y0, x1, y1 = draw.textbbox((0, 0), text)
    margin = 10
    pos = (base.width - (x1 - x0) - margin, base.height - (y1 - y0) - margin)
    draw.text(pos, text, fill=(255, 255, 255, opacity))
    return Image.alpha_composite(base, layer)


def process_file(src: Path, dst_dir: Path, *, max_w=None, max_h=None, fmt=None,
                 trim=False, watermark=None, quality=90) -> Path:
    img = ImageOps.exif_transpose(Image.open(src))
    if trim:
        img = trim_border(img)
    img = resize_fit(img, max_w, max_h)
    if watermark:
        img = add_watermark(img, watermark)
    out_fmt = (fmt or src.suffix.lstrip(".") or "png").lower().replace("jpg", "jpeg")
    if out_fmt == "jpeg":
        img = img.convert("RGB")
    dst = dst_dir / f"{src.stem}.{'jpg' if out_fmt == 'jpeg' else out_fmt}"
    img.save(dst, format=out_fmt.upper(), quality=quality)
    return dst


def process_dir(src_dir: Path, dst_dir: Path, **kw) -> list[Path]:
    dst_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in src_dir.iterdir() if p.suffix.lower() in EXTS)
    return [process_file(p, dst_dir, **kw) for p in files]
