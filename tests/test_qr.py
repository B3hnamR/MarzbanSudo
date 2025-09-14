from __future__ import annotations

from app.utils.qr import generate_qr_png


def _is_png(data: bytes) -> bool:
    return isinstance(data, (bytes, bytearray)) and data.startswith(b"\x89PNG\r\n\x1a\n")


def test_qr_generate_basic_and_special_chars() -> None:
    # Basic
    data1 = generate_qr_png("https://example.com/sub4me/ABC123/")
    assert _is_png(data1)
    assert len(data1) > 100

    # Long + special characters should not crash and produce PNG
    long_token = "A" * 512
    special = "https://example.com/sub4me/" + long_token + "/?q=%E2%9C%93&space=a%20b&sym=+-*/:@"
    data2 = generate_qr_png(special)
    assert _is_png(data2)
    assert len(data2) > 100

