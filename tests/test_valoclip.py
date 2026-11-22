"""valoclip のキル検出を合成動画で確認する。

画面右上に VALORANT 風のキルログ行(左=倒した側の色、右=倒された側の色)を決まった時刻に出し、
背景は動くノイズにする。検出した時刻が出した時刻と合うかを見る。
"""
import csv

import cv2
import numpy as np
import pytest

from valoclip.detect import detect_events, find_entries, iter_frames
from valoclip.report import write_report

W, H, FPS, DUR = 1280, 720, 30, 20
TEAL = (170, 200, 60)   # BGR: 水色
RED = (60, 60, 230)
# (出る時刻, 消える時刻, 種類, 倒された側の名前)
# 8.0 秒は 1 行目が消えるのと同時に新しい行が出る(行数だけ数えると見逃すケース)
# 倒された側のエージェントはチーム内で必ず別なので、アイコン(ここでは図形)も行ごとに違う
FEED = [(3.0, 8.0, "ally", "Kenji", 0), (8.0, 13.0, "ally", "Rin", 1), (8.6, 13.6, "ally", "Sora", 2),
        (12.0, 17.0, "enemy", "meiy", 3), (15.5, 20.0, "ally", "Taro", 4)]


def draw_icon(img, x, y, n, color):
    """エージェントアイコンの代わり。番号ごとに違う図形を描く"""
    cv2.rectangle(img, (x, y), (x + 40, y + 24), color, -1)
    dark = (20, 20, 20)
    if n == 0:
        cv2.circle(img, (x + 20, y + 12), 8, dark, -1)
    elif n == 1:
        cv2.rectangle(img, (x + 6, y + 4), (x + 18, y + 20), dark, -1)
    elif n == 2:
        cv2.line(img, (x + 4, y + 2), (x + 36, y + 22), dark, 4)
    elif n == 3:
        cv2.rectangle(img, (x + 22, y + 4), (x + 36, y + 20), dark, -1)
    else:
        cv2.line(img, (x + 4, y + 22), (x + 36, y + 2), dark, 4)


def draw_frame(t, rng):
    img = rng.integers(40, 110, (H // 8, W // 8, 3), dtype=np.uint8)
    img = cv2.resize(img, (W, H), interpolation=cv2.INTER_LINEAR)
    # 右上の背景にも、ときどき赤っぽいものが映る(誤検出しないか)
    if int(t * 2) % 5 == 0:
        cv2.circle(img, (1100, 200), 12, RED, -1)
    active = [f for f in FEED if f[0] <= t < f[1]]
    for i, (_, _, kind, victim, icon) in enumerate(active):
        y = int(H * 0.09) + i * 30
        x0, x1 = int(W * 0.74), int(W * 0.98)
        mid = (x0 + x1) // 2
        left, right = (TEAL, RED) if kind == "ally" else (RED, TEAL)
        # 半透明の暗い帯(後ろの背景が透けるので、同じ行でも毎フレーム少し変わる)
        band = img[y:y + 24, x0:x1]
        img[y:y + 24, x0:x1] = (band * 0.4 + 18).astype(np.uint8)
        draw_icon(img, x0, y, 9, left)  # 倒した側(視点のプレイヤー)のアイコンは毎回同じ
        cv2.putText(img, "player", (x0 + 46, y + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, left, 2)
        cv2.putText(img, victim, (mid + 30, y + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, right, 2)
        draw_icon(img, x1 - 40, y, icon, right)
    return img


@pytest.fixture(scope="module")
def video(tmp_path_factory):
    path = tmp_path_factory.mktemp("v") / "synthetic.mp4"
    vw = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    rng = np.random.default_rng(0)
    for i in range(FPS * DUR):
        vw.write(draw_frame(i / FPS, rng))
    vw.release()
    return path


def test_find_entries_kinds():
    rng = np.random.default_rng(1)
    entries = find_entries(draw_frame(12.5, rng))  # ally 2 行 + enemy 1 行
    assert [e.kind for e in entries] == ["ally_kill", "ally_kill", "enemy_kill"]


def test_detect_ally_kills(video):
    events = detect_events(iter_frames(video, fps=4))
    times = [e.time for e in events]
    expected = [f[0] for f in FEED if f[2] == "ally"]
    assert len(times) == len(expected), times
    for got, exp in zip(times, expected):
        assert abs(got - exp) <= 0.3, (got, exp)


def test_detect_deaths(video):
    events = detect_events(iter_frames(video, fps=4), kinds=("enemy_kill",))
    assert [round(e.time) for e in events] == [12]


def test_report(video, tmp_path):
    events = detect_events(iter_frames(video, fps=4))
    rows = write_report(video, events, tmp_path, url="https://www.youtube.com/watch?v=abc", offset=60)
    assert len(rows) == 4
    assert (tmp_path / rows[0]["image"]).exists()
    with open(tmp_path / "kills.csv", encoding="utf-8-sig") as f:
        first = next(csv.DictReader(f))
    assert first["time"] == "1:03"                      # 区間開始 60 秒 + 3 秒
    assert first["youtube"].endswith("&t=58s")          # 5 秒前から再生
    assert "本人のキル?" in (tmp_path / "notes.md").read_text(encoding="utf-8")
