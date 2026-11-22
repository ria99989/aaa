"""キルごとの連続画像・クリップ・メモ用テンプレートを書き出す。"""
import csv
import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np

from .timeutil import fmt_time

# キルの瞬間(キルログに出た時刻)からの相対秒。撃つ前の位置取りが見えるよう前を厚めにとる
OFFSETS = (-4.0, -2.0, -1.0, -0.5, -0.2, 0.8)
TILE_W = 640

KIND_JA = {"ally_kill": "味方キル", "enemy_kill": "被キル(味方が倒された)", "manual": "手動指定"}


def grab_frame(cap, t):
    cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, t) * 1000)
    ok, frame = cap.read()
    return frame if ok else None


def contact_sheet(cap, t, offsets=OFFSETS, cols=3, shown=0.0):
    tiles = []
    for off in offsets:
        f = grab_frame(cap, t + off)
        if f is None:
            f = np.zeros((360, 640, 3), np.uint8)
        h = int(f.shape[0] * TILE_W / f.shape[1])
        f = cv2.resize(f, (TILE_W, h), interpolation=cv2.INTER_AREA)
        label = f"{fmt_time(t + off + shown)} ({off:+.1f}s)"
        cv2.rectangle(f, (0, 0), (260, 34), (0, 0, 0), -1)
        cv2.putText(f, label, (8, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        tiles.append(f)
    h = min(x.shape[0] for x in tiles)
    tiles = [x[:h] for x in tiles]
    while len(tiles) % cols:
        tiles.append(np.zeros_like(tiles[0]))
    rows = [np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]
    return np.vstack(rows)


def cut_clip(video, t, out, before=5.0, after=2.0):
    if not shutil.which("ffmpeg"):
        return False
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{max(0, t - before):.2f}", "-i", str(video),
           "-t", f"{before + after:.2f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
           "-c:a", "aac", str(out)]
    return subprocess.run(cmd).returncode == 0


def link(url, t):
    if not url:
        return ""
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}t={max(0, int(t) - 5)}s"


NOTE_TEMPLATE = """### #{n:02d}  {time}  {kind}

![]({img})

{link_line}- 本人のキル?: (はい / いいえ)
- 状況: ラウンド秒数 / 経済(ピストル・エコ・フルバイ) / 人数差
- 位置と角度: オフアングル? 一度に何方向を相手にしていたか
- プリエイム: 撃つ前にクロスヘアが頭の高さ・出てくる位置にあったか
- タイミング: 敵の隙(リロード・スキル直後・移動中)? 味方スキルと同時?
- 撃ち合い: 止まって撃った? ピークの種類(ワイド・ジグル・ショルダー) / 何発 / 初弾ヘッド?
- スキル: 自分のスキルをどう使ったか(入る前・撃ち合い中・逃げ)
- キル後: 押した? 引いた? 次の敵の方向へすぐ向いた?
- 一言で:

"""


def write_report(video, events, outdir, url="", title="", clips=False, offset=0.0):
    """offset: 区間だけ落とした動画のとき、元動画での時刻 = ファイル内の時刻 + offset"""
    outdir = Path(outdir)
    shots = outdir / "shots"
    shots.mkdir(parents=True, exist_ok=True)
    if clips:
        (outdir / "clips").mkdir(exist_ok=True)

    cap = cv2.VideoCapture(str(video))
    rows = []
    notes = [f"# {title or Path(video).stem}\n\n", f"動画: {url or video}\n\n",
             f"検出したキル: {len(events)} 件。1 件ずつ画像を見て「本人のキル?」から埋める。"
             "誤検出は消してよい。\n\n"]
    for n, ev in enumerate(events, 1):
        real = ev.time + offset
        name = f"{n:02d}_{fmt_time(real).replace(':', '-')}"
        img = shots / f"{name}.jpg"
        cv2.imwrite(str(img), contact_sheet(cap, ev.time, shown=offset), [cv2.IMWRITE_JPEG_QUALITY, 85])
        clip = ""
        if clips:
            c = outdir / "clips" / f"{name}.mp4"
            if cut_clip(video, ev.time, c):
                clip = str(c.relative_to(outdir))
        lk = link(url, real)
        rows.append({"no": n, "time": fmt_time(real), "seconds": round(real, 2),
                     "kind": ev.kind, "image": str(img.relative_to(outdir)), "clip": clip, "youtube": lk,
                     "own_kill": "", "situation": "", "angle": "", "preaim": "", "timing": "",
                     "duel": "", "ability": "", "after": "", "summary": ""})
        notes.append(NOTE_TEMPLATE.format(
            n=n, time=fmt_time(real), kind=KIND_JA.get(ev.kind, ev.kind),
            img=img.relative_to(outdir).as_posix(),
            link_line=f"- 動画: {lk}\n" if lk else ""))
    cap.release()

    notes.append("## まとめ(10〜20 件埋めたら書く)\n\n"
                 "- よく出る勝ち方 1:\n- よく出る勝ち方 2:\n- よく出る勝ち方 3:\n"
                 "- 自分の次の数試合の課題(1 つだけ):\n")
    (outdir / "notes.md").write_text("".join(notes), encoding="utf-8")
    # Excel で文字化けしないよう BOM 付き
    with open(outdir / "kills.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["no"])
        w.writeheader()
        w.writerows(rows)
    return rows
