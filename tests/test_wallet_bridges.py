from __future__ import annotations

import asyncio
import types
import pytest

# These tests are lightweight and validate that start router bridges delegate to wallet handlers

@pytest.mark.asyncio
async def test_admin_wallet_settings_bridge(monkeypatch):
    from app.bot.handlers import start as start_handlers

    called = {"settings": False}

    async def fake_settings_handler(message):  # type: ignore[no-untyped-def]
        called["settings"] = True

    # Patch wallet settings handler reference imported in start.py
    monkeypatch.setattr(start_handlers, "wallet_settings_handler", fake_settings_handler)

    class DummyFrom:
        id = 1

    class DummyMessage:
        text = "💼 تنظیمات کیف پول"
        from_user = DummyFrom()

    await start_handlers._btn_admin_wallet_settings(DummyMessage())
    assert called["settings"] is True


@pytest.mark.asyncio
async def test_wallet_manual_add_ref_bridge(monkeypatch):
    from app.bot.handlers import start as start_handlers

    called = {"ref": False}

    async def fake_get_intent_json(key: str):
        # Simulate admin manual-add stage awaiting ref
        return {"stage": "await_ref"}

    async def fake_wallet_manual_add_ref(message):  # type: ignore[no-untyped-def]
        called["ref"] = True

    monkeypatch.setattr(start_handlers, "wallet_manual_add_ref", fake_wallet_manual_add_ref)

    # Patch get_intent_json imported inside the handler via module import
    import app.utils.intent_store as intent_store
    # Monkeypatch the actual function used by the bridge
    monkeypatch.setattr(intent_store, "get_intent_json", fake_get_intent_json)

    class DummyFrom:
        id = 1

    class DummyMessage:
        text = "123456789"
        from_user = DummyFrom()

    await start_handlers._bridge_wallet_manual_add_ref(DummyMessage())
    assert called["ref"] is True


@pytest.mark.asyncio
async def test_wallet_custom_amount_bridge(monkeypatch):
    from app.bot.handlers import start as start_handlers

    called = {"custom": False}

    async def fake_get_intent_json(key: str):
        # Simulate TOPUP intent with amount=-1 (custom amount mode)
        return {"amount": "-1"}

    async def fake_wallet_custom_amount_handler(message):  # type: ignore[no-untyped-def]
        called["custom"] = True

    monkeypatch.setattr(start_handlers, "wallet_custom_amount_handler", fake_wallet_custom_amount_handler)

    import app.utils.intent_store as intent_store
    monkeypatch.setattr(intent_store, "get_intent_json", fake_get_intent_json)

    class DummyFrom:
        id = 1

    class DummyMessage:
        text = "76000"
        from_user = DummyFrom()

    await start_handlers._bridge_wallet_custom_amount(DummyMessage())
    assert called["custom"] is True
