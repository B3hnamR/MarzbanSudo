from __future__ import annotations

import pytest

@pytest.mark.asyncio
async def test_wallet_manual_add_amount_bridge(monkeypatch):
    from app.bot.handlers import start as start_handlers

    called = {"amount": False}

    async def fake_get_intent_json(key: str):
        # Simulate WADM stage awaiting amount
        if key.endswith(":WADM:1") or key == "INTENT:WADM:1":  # be generous
            return {"stage": "await_amount", "user_id": 42, "unit": "TMN"}
        return None

    async def fake_wallet_manual_add_amount_handler(message):  # type: ignore[no-untyped-def]
        called["amount"] = True

    # Patch
    import app.utils.intent_store as intent_store
    monkeypatch.setattr(intent_store, "get_intent_json", fake_get_intent_json)
    monkeypatch.setattr(start_handlers, "wallet_manual_add_amount_handler", fake_wallet_manual_add_amount_handler)

    class DummyFrom:
        id = 1

    class DummyMessage:
        text = "88000"
        from_user = DummyFrom()

    await start_handlers._bridge_wallet_numeric(DummyMessage())
    assert called["amount"] is True
