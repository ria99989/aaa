"""キルログ(画面右上)の行数の変化からキルの瞬間を見つける。

VALORANT のキルログは 1 キル = 1 行で、左に倒した側・右に倒された側が並ぶ。
倒した側が味方なら水色(シアン系)、敵なら赤で表示される。
各フレームでキルログ領域の色を調べて「味方がキルした行」「敵がキルした行」を数え、
行数が増えた瞬間をキルとして記録する。

注意: 味方全員のキルが対象になる。動画の主(視点のプレイヤー)のキルかどうかは
切り出した画像で確認する(report の「本人?」欄)。
"""
from dataclasses import dataclass

import cv2
import numpy as np

# キルログを探す領域(画面に対する比率 x1, y1, x2, y2)。配信レイアウトで違う場合は --roi で変える
DEFAULT_ROI = (0.70, 0.07, 0.995, 0.40)

# HSV(OpenCV: H は 0-179)
ALLY_HSV = ((70, 80, 110), (100, 255, 255))   # 水色・青緑
ENEMY_HSV_1 = ((0, 110, 110), (8, 255, 255))   # 赤(色相の両端)
ENEMY_HSV_2 = ((170, 110, 110), (179, 255, 255))


@dataclass
class Entry:
    y0: int
    y1: int
    kind: str  # "ally_kill" / "enemy_kill"
    sig: np.ndarray = None  # 行の見た目(色マスクを縮小したもの)。同じ行かどうかの照合に使う


@dataclass
class Event:
    time: float
    kind: str


def roi_box(shape, roi):
    h, w = shape[:2]
    x1, y1, x2, y2 = roi
    return int(w * x1), int(h * y1), int(w * x2), int(h * y2)


def color_masks(bgr):
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    ally = cv2.inRange(hsv, *map(np.array, ALLY_HSV))
    enemy = cv2.inRange(hsv, *map(np.array, ENEMY_HSV_1)) | cv2.inRange(hsv, *map(np.array, ENEMY_HSV_2))
    return ally > 0, enemy > 0


def find_entries(frame, roi=DEFAULT_ROI, min_cover=0.06, min_h_ratio=0.012):
    """1 フレームのキルログ行を検出して返す。"""
    x1, y1, x2, y2 = roi_box(frame.shape, roi)
    crop = frame[y1:y2, x1:x2]
    if crop.size == 0:
        return []
    ally, enemy = color_masks(crop)
    width = crop.shape[1]
    colored = ally | enemy
    row_cover = colored.sum(axis=1) / width
    on = row_cover >= min_cover
    min_h = max(3, int(frame.shape[0] * min_h_ratio))

    entries = []
    y = 0
    n = len(on)
    while y < n:
        if not on[y]:
            y += 1
            continue
        start = y
        # 文字の隙間で途切れないよう、2px までの切れ目はつなげる
        gap = 0
        while y < n and (on[y] or gap < 2):
            gap = 0 if on[y] else gap + 1
            y += 1
        end = y - gap
        if end - start < min_h:
            continue
        a = ally[start:end]
        e = enemy[start:end]
        na, ne = a.sum(), e.sum()
        # キルログの行は「倒した側の色」と「倒された側の色」を両方含み、横に長い。
        # 片方の色しかない・幅が狭い・背が高すぎるものは背景とみなす
        if na < 20 or ne < 20 or end - start > frame.shape[0] * 0.06:
            continue
        xs = np.nonzero(a | e)[1]
        if xs.max() - xs.min() < width * 0.3:
            continue
        # 左側(倒した側)の色で判定
        ax = np.nonzero(a)[1].mean()
        ex = np.nonzero(e)[1].mean()
        kind = "ally_kill" if ax < ex else "enemy_kill"
        sig = np.stack([a, e], axis=-1).astype(np.float32)
        sig = cv2.resize(sig, (192, 12), interpolation=cv2.INTER_AREA)
        entries.append(Entry(start + y1, end + y1, kind, sig))
    return entries


def iter_frames(path, fps=4.0, start=0.0, end=None):
    """動画を fps 枚/秒で読み、(秒, フレーム) を返す。"""
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"動画を開けません: {path}")
    vfps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(1, int(round(vfps / fps)))
    if start > 0:
        cap.set(cv2.CAP_PROP_POS_MSEC, start * 1000)
    idx = int(round(start * vfps))
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            t = idx / vfps
            if end is not None and t > end:
                break
            yield t, frame
            # 間のフレームはデコードだけして捨てる
            for _ in range(step - 1):
                if not cap.grab():
                    return
            idx += step
    finally:
        cap.release()


def sig_dist(a, b, win=12):
    """2 行の見た目の違い(0=同じ, 1=全く別)。

    同じ人が続けてキルした行は、倒された側の名前とエージェントアイコンしか違わない。
    全体の平均では埋もれるので、横に細い窓で区切った中で一番違う窓の値を使う。
    """
    col = np.abs(a - b).mean(axis=(0, 2))  # 列ごとの違い
    k = np.ones(win, np.float32) / win
    return float(np.convolve(col, k, mode="valid").max())


def detect_events(frames, roi=DEFAULT_ROI, kinds=("ally_kill",), stable=2, match_thr=0.10, max_miss=2):
    """フレーム列からキルの時刻を返す。

    キルログの各行を見た目で追跡し、初めて見る行が stable 回続けて見えたら 1 キルとする。
    時刻はその行が最初に見えたフレーム。行が消える・上下にずれる・同時に出入りしても数がずれない。
    """
    events = []
    tracks = []  # dict(sig, kind, first, seen, miss, done)
    for t, frame in frames:
        entries = [e for e in find_entries(frame, roi) if e.kind in kinds]
        # 既存の行と近い順に 1 対 1 で対応づける
        pairs = sorted(
            (sig_dist(tr["sig"], e.sig), ti, ei)
            for ti, tr in enumerate(tracks) for ei, e in enumerate(entries) if tr["kind"] == e.kind)
        used_t, used_e = set(), set()
        for d, ti, ei in pairs:
            if d > match_thr or ti in used_t or ei in used_e:
                continue
            used_t.add(ti)
            used_e.add(ei)
            tr = tracks[ti]
            tr["sig"] = entries[ei].sig
            tr["seen"] += 1
            tr["miss"] = 0
        for ti, tr in enumerate(tracks):
            if ti not in used_t:
                tr["miss"] += 1
        tracks = [tr for tr in tracks if tr["miss"] <= max_miss]
        for ei, e in enumerate(entries):
            if ei not in used_e:
                tracks.append(dict(sig=e.sig, kind=e.kind, first=t, seen=1, miss=0, done=False))
        for tr in tracks:
            if not tr["done"] and tr["seen"] >= stable:
                tr["done"] = True
                events.append(Event(tr["first"], tr["kind"]))
    events.sort(key=lambda e: e.time)
    return events
