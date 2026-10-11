import cv2
import numpy as np
from PIL import Image


def _bgr(img: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)


def foreground_mask(img: Image.Image, margin: float = 0.03, iters: int = 5,
                    keep_largest: bool = True) -> np.ndarray:
    """GrabCut で前景マスク(0/255, uint8)を返す。

    縁(margin)を背景、色の離れた画素を前景候補として初期化する。処理は長辺 640px に縮小して
    行い、マスクを元サイズに戻すので大きい画像でも速い。
    """
    bgr = _bgr(img)
    h0, w0 = bgr.shape[:2]
    s = min(1.0, 640 / max(h0, w0))
    small = cv2.resize(bgr, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if s < 1 else bgr
    h, w = small.shape[:2]
    m = max(2, int(min(h, w) * margin))

    # 縁の画素から背景色を推定し、そこから離れた画素を前景候補にする
    border = np.concatenate([small[:m].reshape(-1, 3), small[-m:].reshape(-1, 3),
                             small[:, :m].reshape(-1, 3), small[:, -m:].reshape(-1, 3)]).astype(np.float32)
    bg_color = np.median(border, axis=0)
    spread = np.linalg.norm(border - bg_color, axis=1).std() + 1.0
    dist = np.linalg.norm(small.astype(np.float32) - bg_color, axis=2)
    thr = max(25.0, 3 * spread)

    mask = np.full((h, w), cv2.GC_PR_BGD, np.uint8)
    mask[dist > thr] = cv2.GC_PR_FGD
    mask[dist > thr * 2] = cv2.GC_FGD
    mask[:m], mask[-m:], mask[:, :m], mask[:, -m:] = cv2.GC_BGD, cv2.GC_BGD, cv2.GC_BGD, cv2.GC_BGD
    # 前景候補が皆無なら中央矩形を初期値にする
    if not (mask == cv2.GC_PR_FGD).any() and not (mask == cv2.GC_FGD).any():
        mask[h // 5: -h // 5, w // 5: -w // 5] = cv2.GC_PR_FGD

    bgd, fgd = np.zeros((1, 65)), np.zeros((1, 65))
    cv2.grabCut(small, mask, None, bgd, fgd, iters, cv2.GC_INIT_WITH_MASK)
    fg = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)

    # 小さなゴミ除去・穴埋め(keep_largest なら最大連結成分のみ残す)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    fg = cv2.morphologyEx(cv2.morphologyEx(fg, cv2.MORPH_OPEN, k), cv2.MORPH_CLOSE, k)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(fg)
    if keep_largest and n > 1:
        keep = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        fg = np.where(labels == keep, 255, 0).astype(np.uint8)
    out = cv2.resize(fg, (w0, h0), interpolation=cv2.INTER_LINEAR)
    return cv2.GaussianBlur(out, (0, 0), 1.0)  # 輪郭をなめらかに


def cutout(img: Image.Image, **kw) -> Image.Image:
    """背景を透過にした RGBA 画像。"""
    out = img.convert("RGBA")
    out.putalpha(Image.fromarray(foreground_mask(img, **kw)))
    return out


def detect_boxes(img: Image.Image, min_area_ratio: float = 0.005) -> list[tuple[int, int, int, int]]:
    """前景を輪郭分離して (x, y, w, h) のリストを返す(複数物体対応)。"""
    mask = foreground_mask(img, keep_largest=False)
    n, _, stats, _ = cv2.connectedComponentsWithStats((mask > 127).astype(np.uint8))
    area_min = min_area_ratio * mask.size
    return [tuple(int(v) for v in stats[i, :4]) for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] >= area_min]


def draw_boxes(img: Image.Image, boxes) -> Image.Image:
    bgr = _bgr(img)
    for x, y, w, h in boxes:
        cv2.rectangle(bgr, (x, y), (x + w, y + h), (0, 200, 0), max(2, img.width // 300))
    return Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))


def composite(rgba: Image.Image, bg_color=(255, 255, 255)) -> Image.Image:
    """透過画像を単色背景に合成(ECサイト向けの白背景など)。"""
    base = Image.new("RGB", rgba.size, bg_color)
    base.paste(rgba, mask=rgba.getchannel("A"))
    return base
