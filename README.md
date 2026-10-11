# 月5万円プロジェクト

目標: 週20時間で月5万円の副収入。専門は AI・画像処理。

- `imgbatch/` … ポートフォリオ兼・販売用の画像一括処理ツール(`python -m imgbatch 入力 出力 --max-width 1200 --format webp --trim`)
- `receipt_ocr/` … 領収書・レシート画像 → CSV(日付/店名/合計/要確認フラグ)。`python -m receipt_ocr samples out.csv`
  - 要: `apt install tesseract-ocr tesseract-ocr-jpn`(Mac: `brew install tesseract tesseract-lang`)
  - 抽出できない項目がある行は `needs_review=True` になり、目視確認の対象になります
  - `samples/` はダミー画像(生成スクリプト付き)。実在のレシートは含みません
- `docs/PLAN.md` … 4週間の行動計画と収益目標
- `docs/GIGS.md` … ココナラ等への出品文ドラフト
- `docs/PROPOSALS.md` … クラウドソーシング提案文テンプレート

テスト: `pip install -r requirements.txt && pytest`
