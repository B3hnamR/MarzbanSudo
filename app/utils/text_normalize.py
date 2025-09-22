from __future__ import annotations

from typing import Optional

# Common text normalization utilities for reply-keyboard buttons and general text matching
# - Removes zero-width and direction control chars
# - Unifies Arabic Yeh/Kaf to Persian variants
# - Collapses multiple spaces and normalizes NBSP/NNBSP

_REMOVE_CHARS = "\u200c\u200d\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u202f\ufeff\ufe0f"
_SUBS = str.maketrans({"\u00a0": " ", "\u202f": " "})


def normalize_btn_text(value: Optional[str]) -> str:
    """Normalize a UI button text for robust matching across Unicode variants."""
    if not isinstance(value, str):
        return ""
    t = value.strip().translate(_SUBS)
    t = t.translate(str.maketrans("", "", _REMOVE_CHARS))
    # unify Arabic Yeh/Kaf to Persian Yeh/Kaf
    t = t.replace("\u064a", "\u06cc").replace("\u0643", "\u06a9")
    # collapse spaces
    t = " ".join(t.split())
    return t


def text_matches(a: Optional[str], b: Optional[str]) -> bool:
    """Compare two texts after normalization."""
    return normalize_btn_text(a) == normalize_btn_text(b)
