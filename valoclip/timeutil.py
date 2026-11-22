def parse_time(s):
    """'1:23:45' / '83' / '1:23.5' -> 秒"""
    s = str(s).strip()
    sec = 0.0
    for part in s.split(":"):
        sec = sec * 60 + float(part)
    return sec


def fmt_time(sec):
    sec = max(0, int(round(sec)))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
