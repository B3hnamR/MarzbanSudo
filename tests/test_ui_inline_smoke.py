import asyncio
import types
import pytest
from decimal import Decimal

# Import target functions from the user-facing flow
from app.bot.handlers.plans import _present_final_confirm, cb_plan_cancel


class FakeMessage:
    def __init__(self):
        self.last_text = None
        self.last_markup = None
        self.edited = False

    async def edit_text(self, text, reply_markup=None, **kwargs):
        self.last_text = text
        self.last_markup = reply_markup
        self.edited = True

    async def answer(self, text, reply_markup=None, **kwargs):
        # fallback path used in handlers
        self.last_text = text
        self.last_markup = reply_markup
        self.edited = False


class FakeCb:
    def __init__(self):
        self.message = FakeMessage()
        self.answered = False

    async def answer(self, *args, **kwargs):
        self.answered = True


@pytest.mark.asyncio
async def test_present_final_confirm_renders_inline_with_back():
    # Arrange: stub plan object with attributes used by the function
    plan = types.SimpleNamespace(
        price=Decimal("100000"),  # 10,000 Toman
        data_limit_bytes=10 * 1024**3,  # 10GB
        duration_days=30,
        title="پلن تستی",
    )
    tpl_id = 123
    cb = FakeCb()

    # Act
    await _present_final_confirm(cb, tpl_id, username_eff="testuser", plan=plan)

    # Assert
    assert cb.message.last_text is not None
    assert "پلن تستی" in cb.message.last_text
    assert "10GB" in cb.message.last_text
    assert "30 روز" in cb.message.last_text
    # Inline keyboard with back button exists and points to plan:mode:sel:<tpl_id>
    markup = cb.message.last_markup
    assert markup is not None
    # flatten buttons text and callback_data
    buttons = [btn for row in getattr(markup, "inline_keyboard", []) for btn in row]
    back = [b for b in buttons if getattr(b, "text", "") == "⬅️ بازگشت"]
    assert back, "Back button not found"
    assert back[0].callback_data == f"plan:mode:sel:{tpl_id}"


@pytest.mark.asyncio
async def test_cb_plan_cancel_edits_message():
    cb = FakeCb()

    # Act
    await cb_plan_cancel(cb)

    # Assert
    assert cb.answered is True
    assert cb.message.last_text == "❌ خرید لغو شد"
    assert cb.message.edited in (True, False)  # accept either edit_text or answer fallback
