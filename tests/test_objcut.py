import numpy as np
from PIL import Image

from objcut.core import composite, cutout, detect_boxes, foreground_mask
from samples.make_objects import make


def _iou(pred, gt):
    p, g = np.array(pred) > 127, np.array(gt) > 127
    return (p & g).sum() / (p | g).sum()


def test_single_object_mask_iou():
    img, gt = make(1, n_objects=1)
    assert _iou(foreground_mask(img), gt) > 0.93


def test_detect_two_objects():
    img, _ = make(2, n_objects=2)
    boxes = detect_boxes(img)
    assert len(boxes) == 2
    xs = sorted(b[0] for b in boxes)
    assert abs(xs[0] - 90) < 8 and abs(xs[1] - 360) < 8


def test_cutout_and_white_composite():
    img, _ = make(1, n_objects=1)
    rgba = cutout(img)
    assert rgba.mode == "RGBA" and rgba.getpixel((5, 5))[3] < 10
    assert composite(rgba).getpixel((5, 5)) == (255, 255, 255)
