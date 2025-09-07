from __future__ import annotations

# This test verifies that the wallet-purchase flow persists an immutable
# snapshot of plan fields into Order creation (Step 1 change).
# It performs a static source check to avoid DB/Telegram dependencies in CI.

from pathlib import Path

REQUIRED_TOKENS = [
    "plan_template_id=",
    "plan_title=",
    "plan_price=",
    "plan_currency=",
    "plan_duration_days=",
    "plan_data_limit_bytes=",
]


def test_order_snapshot_fields_present() -> None:
    root = Path(__file__).resolve().parents[1]
    plans_py = root / "app" / "bot" / "handlers" / "plans.py"
    src = plans_py.read_text(encoding="utf-8")
    # Basic sanity: ensure Order(...) exists in the file
    assert "Order(" in src, "Order constructor not found in plans.py"
    # Ensure all snapshot tokens are present in the source
    missing = [tok for tok in REQUIRED_TOKENS if tok not in src]
    assert not missing, f"Missing snapshot fields in Order creation: {missing}"
