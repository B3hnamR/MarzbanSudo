from __future__ import annotations

from io import BytesIO
from typing import Optional

import qrcode


def generate_qr_png(data: str, *, size: int = 400, border: int = 2) -> bytes:
    """Generate a QR code PNG for the given data.

    - Uses qrcode with PIL backend.
    - Resizes output to exactly `size` x `size` pixels (nearest) if needed.
    - Returns PNG bytes suitable for sending as a photo.
    """
    if not isinstance(data, str) or not data:
        raise ValueError("data must be a non-empty string")

    qr = qrcode.QRCode(box_size=10, border=max(0, int(border)))
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # Try to resize to exact `size` if possible
    try:
        from PIL import Image  # type: ignore
        if getattr(img, "size", None) != (size, size):
            img = img.resize((size, size), Image.NEAREST)
    except Exception:
        # Fallback: keep original size
        pass

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


__all__ = ["generate_qr_png"]
