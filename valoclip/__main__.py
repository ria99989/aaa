import argparse
import re
import sys
from pathlib import Path

import cv2

from .detect import DEFAULT_ROI, Event, detect_events, find_entries, iter_frames, roi_box
from .report import write_report
from .timeutil import parse_time


def is_url(s):
    return re.match(r"https?://", s) is not None


def download(url, outdir, section=None, max_height=1080):
    """yt-dlp で動画を保存し、(ファイル一覧, url, タイトル) を返す。再生リストも可。"""
    try:
        import yt_dlp
        from yt_dlp.utils import download_range_func
    except ImportError:
        sys.exit("yt-dlp が必要です: pip install yt-dlp")
    outdir.mkdir(parents=True, exist_ok=True)
    opts = {
        "format": f"bv*[height<={max_height}]+ba/b[height<={max_height}]/b",
        "outtmpl": str(outdir / "%(id)s.%(ext)s"),
        "merge_output_format": "mp4",
        "quiet": True, "no_warnings": True,
    }
    if section:
        a, b = section
        opts["download_ranges"] = download_range_func(None, [(a, b)])
        opts["force_keyframes_at_cuts"] = True
        opts["outtmpl"] = str(outdir / f"%(id)s_{int(a)}-{int(b)}.%(ext)s")
    results = []
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        items = info.get("entries") or [info]
        for it in items:
            if not it:
                continue
            path = Path(ydl.prepare_filename(it)).with_suffix(".mp4")
            if not path.exists():
                cands = sorted(outdir.glob(path.stem + ".*"))
                path = cands[0] if cands else path
            results.append((path, it.get("webpage_url") or url, it.get("title", ""), it.get("id", path.stem)))
    return results


def parse_roi(s):
    v = tuple(float(x) for x in s.split(","))
    if len(v) != 4:
        raise argparse.ArgumentTypeError("--roi は x1,y1,x2,y2 (0〜1 の比率)")
    return v


def parse_section(s):
    a, b = s.split("-")
    return parse_time(a), parse_time(b)


def cmd_analyze(a):
    out = Path(a.out)
    targets = []  # (ファイル, URL, タイトル, ID, 元動画との時刻差, 解析区間)
    for src in a.inputs:
        if is_url(src):
            print(f"ダウンロード中: {src}")
            # 区間指定時はその区間だけ落とすので、ファイル内 0 秒 = 元動画の区間開始
            off = a.section[0] if a.section else 0.0
            for path, url, title, vid in download(src, out / "videos", a.section, a.max_height):
                targets.append((path, url, title, vid, off, (0.0, None)))
        else:
            p = Path(src)
            rng = a.section or (0.0, None)
            targets.append((p, "", p.stem, p.stem, 0.0, rng))

    for path, url, title, vid, off, (start, end) in targets:
        print(f"解析中: {title or path.name}")
        if a.times:
            events = [Event(parse_time(t) - off, "manual") for t in a.times.split(",")]
        else:
            kinds = ("ally_kill", "enemy_kill") if a.deaths else ("ally_kill",)
            frames = iter_frames(path, fps=a.fps, start=start, end=end)
            events = detect_events(frames, roi=a.roi, kinds=kinds)
        rows = write_report(path, events, out / vid, url=url, title=title, clips=a.clips, offset=off)
        print(f"  {len(rows)} 件 -> {out / vid / 'notes.md'}")


def cmd_calibrate(a):
    cap = cv2.VideoCapture(a.video)
    cap.set(cv2.CAP_PROP_POS_MSEC, parse_time(a.at) * 1000)
    ok, frame = cap.read()
    if not ok:
        sys.exit("その時刻のフレームを読めません")
    x1, y1, x2, y2 = roi_box(frame.shape, a.roi)
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
    entries = find_entries(frame, a.roi)
    for e in entries:
        col = (255, 255, 0) if e.kind == "ally_kill" else (0, 0, 255)
        cv2.rectangle(frame, (x1, e.y0), (x2, e.y1), col, 2)
        cv2.putText(frame, e.kind, (x1 - 150, e.y1), cv2.FONT_HERSHEY_SIMPLEX, 0.6, col, 2)
    cv2.imwrite(a.out, frame)
    print(f"黄枠 = 探す領域、水色枠 = 味方キル行、赤枠 = 被キル行。{len(entries)} 行 -> {a.out}")


def main():
    ap = argparse.ArgumentParser(prog="valoclip", description="VALORANT の動画からキルの場面を切り出す")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("analyze", help="動画(URL かファイル)からキルを検出してまとめる")
    p.add_argument("inputs", nargs="+", help="YouTube の URL(再生リスト可)か動画ファイル")
    p.add_argument("-o", "--out", default="valo_out")
    p.add_argument("--section", type=parse_section, help="解析する区間 例: 12:00-30:00(長い配信向け)")
    p.add_argument("--times", help="検出せず、この時刻を使う 例: 1:23,4:56")
    p.add_argument("--roi", type=parse_roi, default=DEFAULT_ROI, help="キルログの領域 x1,y1,x2,y2")
    p.add_argument("--fps", type=float, default=4.0, help="1 秒に調べる枚数")
    p.add_argument("--deaths", action="store_true", help="味方が倒された場面も出す")
    p.add_argument("--clips", action="store_true", help="キル前後 7 秒の mp4 も書き出す(ffmpeg 必要)")
    p.add_argument("--max-height", type=int, default=1080)
    p.set_defaults(func=cmd_analyze)

    c = sub.add_parser("calibrate", help="キルログ領域が合っているか画像で確認する")
    c.add_argument("video")
    c.add_argument("--at", default="60", help="確認する時刻(キルログが出ている場面)")
    c.add_argument("--roi", type=parse_roi, default=DEFAULT_ROI)
    c.add_argument("-o", "--out", default="calibrate.png")
    c.set_defaults(func=cmd_calibrate)

    a = ap.parse_args()
    a.func(a)


main()
