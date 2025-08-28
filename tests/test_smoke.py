from __future__ import annotations

import os
import types


def test_healthcheck_import() -> None:
    import app.healthcheck as hc
    assert isinstance(hc, types.ModuleType)


def test_env_example_keys_present() -> None:
    # Ensure critical env keys exist in example template for documentation correctness
    example = open('.env.example', 'r', encoding='utf-8').read()
    for key in [
        'TELEGRAM_BOT_TOKEN',
        'MARZBAN_BASE_URL',
        'MARZBAN_ADMIN_USERNAME',
        'MARZBAN_ADMIN_PASSWORD',
        'DB_URL',
    ]:
        assert key in example
