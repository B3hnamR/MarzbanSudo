import os
import sys

# Minimal healthcheck: validate ENV and token presence

def main() -> int:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("missing TELEGRAM_BOT_TOKEN", file=sys.stderr)
        return 1
    # In future, we can test DB and Marzban connectivity here
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
