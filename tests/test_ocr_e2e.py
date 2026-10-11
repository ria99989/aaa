import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract 未インストール")
def test_sample_receipts(tmp_path):
    out = tmp_path / "o.csv"
    subprocess.run([sys.executable, "-m", "receipt_ocr", str(ROOT / "samples"), str(out)],
                   check=True, cwd=ROOT)
    text = out.read_text(encoding="utf-8-sig")
    assert "2025-03-14" in text and "2180" in text and "4620" in text
