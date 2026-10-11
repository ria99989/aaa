"""OCR 前の画像補正: 影除去・傾き補正・二値化。OpenCV を使用。"""
import cv2
import numpy as np
from PIL import Image


def _to_gray(img: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2GRAY)


def remove_shadow(gray: np.ndarray) -> np.ndarray:
    """背景(照明ムラ・影)を推定して割り算で打ち消す。"""
    k = max(15, (min(gray.shape) // 20) | 1)
    bg = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    bg = cv2.medianBlur(bg, k if k % 2 else k + 1)
    return cv2.divide(gray, bg, scale=255)


def estimate_skew(gray: np.ndarray) -> float:
    """文字画素の minAreaRect から傾き角(度)を推定。-45〜45 に正規化。"""
    bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    pts = cv2.findNonZero(bw)
    if pts is None or len(pts) < 50:
        return 0.0
    angle = cv2.minAreaRect(pts)[-1]
    if angle > 45:
        angle -= 90
    return float(angle)


def rotate(gray: np.ndarray, angle: float) -> np.ndarray:
    h, w = gray.shape
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(gray, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def deskew(gray: np.ndarray, max_angle: float = 15.0) -> np.ndarray:
    a = estimate_skew(gray)
    return rotate(gray, a) if 0.3 < abs(a) <= max_angle else gray


def enhance(img: Image.Image, target_width: int = 1400) -> Image.Image:
    gray = _to_gray(img)
    if gray.shape[1] < target_width:
        s = target_width / gray.shape[1]
        gray = cv2.resize(gray, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC)
    gray = remove_shadow(gray)
    gray = deskew(gray)
    gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
    return Image.fromarray(gray)
