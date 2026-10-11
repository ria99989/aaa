from receipt_ocr.parse import extract_date, extract_store, extract_total, parse_receipt


def test_date_formats():
    assert extract_date("2025年3月14日") == "2025-03-14"
    assert extract_date("2025/11/02 12:00") == "2025-11-02"
    assert extract_date("令和7年1月5日") == "2025-01-05"
    assert extract_date("日付なし") is None


def test_total_prefers_keyword_over_larger_number():
    text = "商品A ¥500\n合計 ¥1,200\n預り ¥5,000"
    assert extract_total(text) == 1200


def test_total_ignores_subtotal_and_falls_back_to_max():
    assert extract_total("小計 ¥900\n合計 ¥990") == 990
    assert extract_total("A 100円\nB 2,500円") == 2500


def test_store_skips_header_and_phone():
    assert extract_store("領収書\nTEL 03-1234-5678\nサンプル商店\n") == "サンプル商店"


def test_parse_receipt_fullwidth():
    r = parse_receipt("サンプル商店\n２０２５年３月１４日\n合計　￥２，１８０")
    assert r == {"date": "2025-03-14", "store": "サンプル商店", "total": 2180}
