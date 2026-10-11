"""店名・品目テキストから勘定科目を推定する(キーワードルール。ユーザー定義で上書き可)。"""
import json
from pathlib import Path

DEFAULT_RULES: dict[str, list[str]] = {
    "旅費交通費": ["jr", "鉄道", "タクシー", "バス", "駐車", "高速", "航空", "交通", "suica", "pasmo"],
    "会議費": ["カフェ", "コーヒー", "珈琲", "喫茶", "スターバックス", "ドトール", "タリーズ"],
    "接待交際費": ["居酒屋", "レストラン", "焼肉", "寿司", "料亭", "バー", "飲食"],
    "消耗品費": ["文具", "文房具", "ホームセンター", "百均", "ダイソー", "ヨドバシ", "ビックカメラ", "アスクル", "電池"],
    "新聞図書費": ["書店", "書籍", "本屋", "雑誌", "技術書", "紀伊國屋", "ブックオフ"],
    "通信費": ["携帯", "モバイル", "ドコモ", "ソフトバンク", "au", "インターネット", "切手", "郵便"],
    "水道光熱費": ["電力", "電気", "ガス", "水道"],
    "雑費": [],
}
FALLBACK = "要確認"


def load_rules(path: Path | None) -> dict[str, list[str]]:
    if path is None:
        return DEFAULT_RULES
    return json.loads(Path(path).read_text(encoding="utf-8"))


def classify(text: str | None, rules: dict[str, list[str]] = DEFAULT_RULES) -> str:
    if not text:
        return FALLBACK
    t = text.lower()
    for account, words in rules.items():
        if any(w.lower() in t for w in words):
            return account
    return FALLBACK
