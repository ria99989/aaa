from PIL import Image

from imgbatch.core import process_dir, resize_fit, trim_border


def test_resize_keeps_ratio_and_no_upscale():
    assert resize_fit(Image.new("RGB", (400, 200)), 100, None).size == (100, 50)
    assert resize_fit(Image.new("RGB", (50, 50)), 100, 100).size == (50, 50)


def test_trim_border():
    img = Image.new("RGB", (100, 100), "white")
    img.paste(Image.new("RGB", (20, 30), "red"), (40, 10))
    assert trim_border(img).size == (20, 30)


def test_process_dir(tmp_path):
    src, dst = tmp_path / "s", tmp_path / "d"
    src.mkdir()
    Image.new("RGB", (800, 600), "blue").save(src / "a.png")
    out = process_dir(src, dst, max_w=200, fmt="jpeg", watermark="demo")
    assert out[0].suffix == ".jpg" and Image.open(out[0]).size == (200, 150)
