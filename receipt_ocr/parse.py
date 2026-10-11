"""OCR テキストからの項目抽出(Tesseract に依存しない純粋関数)。"""
import re
import unicodedata

_DATE_PATTERNS = [
    re.compile(r"(20\d{2})\s*[年/.\-]\s*(\d{1,2})\s*[月/.\-]\s*(\d{1,2})"),
    re.compile(r"(?:令和|R)\s*(\d{1,2})\s*[年/.\-]\s*(\d{1,2})\s*[月/.\-]\s*(\d{1,2})"),
]
_TOTAL_KEYWORDS = re.compile(r"(合\s*計|総\s*合\s*計|お?支払|ご請求|total|税込)", re.I)
_AMOUNT = re.compile(r"[¥\\]?\s*(\d{1,3}(?:,\d{3})+|\d+)\s*円?")
_SKIP_STORE = re.compile(r"(領収|レシート|receipt|様|tel|電話|\d{2,4}-\d{2,4}-\d{3,4}|登録番号|^\W*$)", re.I)


def normalize(text: str) -> str:
    """全角→半角、空白のゆれを正規化。"""
    text = unicodedata.normalize("NFKC", text)
    # 日本語文字間に入る OCR 由来の空白を除去
    return re.sub(r"(?<=[^\x00-\x7f]) (?=[^\x00-\x7f])", "", text)


def extract_date(text: str) -> str | None:
    for i, pat in enumerate(_DATE_PATTERNS):
        m = pat.search(text)
        if m:
            y, mo, d = (int(g) for g in m.groups())
            if i == 1:
                y += 2018
            if 1 <= mo <= 12 and 1 <= d <= 31:
                return f"{y:04d}-{mo:02d}-{d:02d}"
    return None


def _amounts(line: str) -> list[int]:
    return [int(a.replace(",", "")) for a in _AMOUNT.findall(line)]


def extract_total(text: str) -> int | None:
    """「合計」等のキーワード行の金額を優先。無ければ全体の最大金額。"""
    lines = text.splitlines()
    keyed = []
    for i, line in enumerate(lines):
        if _TOTAL_KEYWORDS.search(line) and "小計" not in line:
            vals = _amounts(line) or (_amounts(lines[i + 1]) if i + 1 < len(lines) else [])
            keyed += vals
    if keyed:
        return max(keyed)
    allv = [v for line in lines for v in _amounts(line) if v < 10_000_000]
    return max(allv) if allv else None


def extract_store(text: str) -> str | None:
    """先頭付近で、領収書見出し・電話番号などを除いた最初の行を店名とみなす。"""
    for line in text.splitlines()[:8]:
        line = line.strip()
        if len(line) >= 2 and not _SKIP_STORE.search(line) and not _DATE_PATTERNS[0].search(line):
            return line
    return None


def parse_receipt(raw_text: str) -> dict:
    text = normalize(raw_text)
    return {"date": extract_date(text), "store": extract_store(text), "total": extract_total(text)}
