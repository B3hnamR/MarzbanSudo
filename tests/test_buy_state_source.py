from __future__ import annotations

from pathlib import Path


def test_buy_state_uses_intent_store_not_dicts() -> None:
    root = Path(__file__).resolve().parents[1]
    src = (root / "app" / "bot" / "handlers" / "plans.py").read_text(encoding="utf-8")
    # Old volatile dict states must be gone
    for tok in [
        "_PURCHASE_SELECTION",
        "_PURCHASE_MODE",
        "_PURCHASE_EXT_SERVICE",
        "_PURCHASE_CUSTOM_PENDING",
    ]:
        assert tok not in src, f"old state token present: {tok}"

    # Intent store should be referenced
    assert "from app.utils.intent_store import set_intent_json" in src
    assert "get_intent_json" in src
    assert "clear_intent" in src

