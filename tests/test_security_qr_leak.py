from __future__ import annotations

from pathlib import Path


def test_plans_uses_local_qr_and_no_third_party() -> None:
    root = Path(__file__).resolve().parents[1]
    src = (root / "app" / "bot" / "handlers" / "plans.py").read_text(encoding="utf-8")
    assert "api.qrserver.com" not in src
    assert "generate_qr_png" in src or "utils.qr" in src
    # Should use aiogram BufferedInputFile to send photo bytes
    assert "BufferedInputFile" in src

