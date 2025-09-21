from pathlib import Path

path = Path('app/bot/handlers/start.py')
text = path.read_text(encoding='utf-8')
replacements = {
    '@router.message(F.text.in_({"?? ????????", "?? ????????? ??"}))\nasync def _btn_orders(message: Message) -> None:\n    await orders_handler(message)\n':
    '@router.message(F.text.in_({"?? ????????", "?? ????????? ??"}))\nasync def _btn_orders(message: Message) -> None:\n    logger.info("start.btn_orders", extra={'extra': {'uid': getattr(getattr(message, 'from_user', None), 'id', None)}})\n    await orders_handler(message)\n',
    '@router.message(F.text.in_({"?? ?????", "?? ????? ??"}))\nasync def _btn_account(message: Message) -> None:\n    await account_handler(message)\n':
    '@router.message(F.text.in_({"?? ?????", "?? ????? ??"}))\nasync def _btn_account(message: Message) -> None:\n    logger.info("start.btn_account", extra={'extra': {'uid': getattr(getattr(message, 'from_user', None), 'id', None)}})\n    await account_handler(message)\n',
    '@router.message(F.text == "?? ??? ???")\nasync def _btn_wallet(message: Message) -> None:\n    await wallet_menu_handler(message)\n':
    '@router.message(F.text == "?? ??? ???")\nasync def _btn_wallet(message: Message) -> None:\n    logger.info("start.btn_wallet", extra={'extra': {'uid': getattr(getattr(message, 'from_user', None), 'id', None)}})\n    await wallet_menu_handler(message)\n'
}
for old, new in replacements.items():
    if old not in text:
        raise SystemExit('pattern not found')
    text = text.replace(old, new)
path.write_text(text, encoding='utf-8')
