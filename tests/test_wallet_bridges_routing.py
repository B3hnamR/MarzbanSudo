from __future__ import annotations

import pytest

@pytest.mark.asyncio
async def test_numeric_priority_manual_add_over_limits_and_custom(monkeypatch):
    from app.bot.handlers import start as start_handlers

    called = {"amount": False, "limits": False, "custom": False}

    async def fake_get_intent_json(key: str):
        if key == "INTENT:WADM:1":
            return {"stage": "await_amount", "user_id": 42, "unit": "TMN"}
        if key == "INTENT:TOPUP:1":
            return {"amount": "-1"}
        return None

    async def fake_wallet_manual_add_amount_handler(message):  # type: ignore
        called["amount"] = True

    async def fake_wallet_limits_numeric_input_handler(message):  # type: ignore
        called["limits"] = True

    async def fake_wallet_custom_amount_handler(message):  # type: ignore
        called["custom"] = True

    import app.utils.intent_store as intent_store
    monkeypatch.setattr(intent_store, "get_intent_json", fake_get_intent_json)

    monkeypatch.setattr(start_handlers, "wallet_manual_add_amount_handler", fake_wallet_manual_add_amount_handler)
    monkeypatch.setattr(start_handlers, "wallet_limits_numeric_input_handler", fake_wallet_limits_numeric_input_handler)
    monkeypatch.setattr(start_handlers, "wallet_custom_amount_handler", fake_wallet_custom_amount_handler)

    class DummyFrom:
        id = 1

    class DummyMessage:
        text = "88000"
        from_user = DummyFrom()

    await start_handlers._bridge_wallet_numeric(DummyMessage())

    assert called["amount"] is True
    assert called["limits"] is False
    assert called["custom"] is False


@pytest.mark.asyncio
async def test_numeric_routes_to_limits_when_no_wadm_and_no_custom(monkeypatch):
    from app.bot.handlers import start as start_handlers

    called = {"amount": False, "limits": False, "custom": False}

    async def fake_get_intent_json(key: str):
        return None

    async def fake_wallet_manual_add_amount_handler(message):  # type: ignore
        called["amount"] = True

    async def fake_wallet_limits_numeric_input_handler(message):  # type: ignore
        called["limits"] = True

    async def fake_wallet_custom_amount_handler(message):  # type: ignore
        called["custom"] = True

    import app.utils.intent_store as intent_store
    monkeypatch.setattr(intent_store, "get_intent_json", fake_get_intent_json)

    monkeypatch.setattr(start_handlers, "wallet_manual_add_amount_handler", fake_wallet_manual_add_amount_handler)
    monkeypatch.setattr(start_handlers, "wallet_limits_numeric_input_handler", fake_wallet_limits_numeric_input_handler)
    monkeypatch.setattr(start_handlers, "wallet_custom_amount_handler", fake_wallet_custom_amount_handler)

    class DummyFrom:
        id = 1

    class DummyMessage:
        text = "150000"
        from_user = DummyFrom()

    await start_handlers._bridge_wallet_numeric(DummyMessage())

    assert called["limits"] is True
    assert called["amount"] is False
    assert called["custom"] is False


@pytest.mark.asyncio
async def test_numeric_routes_to_custom_when_topup_amount_minus_one(monkeypatch):
    from app.bot.handlers import start as start_handlers

    called = {"amount": False, "limits": False, "custom": False}

    async def fake_get_intent_json(key: str):
        if key == "INTENT:TOPUP:1":
            return {"amount": "-1"}
        return None

    async def fake_wallet_manual_add_amount_handler(message):  # type: ignore
        called["amount"] = True

    async def fake_wallet_limits_numeric_input_handler(message):  # type: ignore
        called["limits"] = True

    async def fake_wallet_custom_amount_handler(message):  # type: ignore
        called["custom"] = True

    import app.utils.intent_store as intent_store
    monkeypatch.setattr(intent_store, "get_intent_json", fake_get_intent_json)

    monkeypatch.setattr(start_handlers, "wallet_manual_add_amount_handler", fake_wallet_manual_add_amount_handler)
    monkeypatch.setattr(start_handlers, "wallet_limits_numeric_input_handler", fake_wallet_limits_numeric_input_handler)
    monkeypatch.setattr(start_handlers, "wallet_custom_amount_handler", fake_wallet_custom_amount_handler)

    class DummyFrom:
        id = 1

    class DummyMessage:
        text = "88000"
        from_user = DummyFrom()

    await start_handlers._bridge_wallet_numeric(DummyMessage())

    assert called["custom"] is True
