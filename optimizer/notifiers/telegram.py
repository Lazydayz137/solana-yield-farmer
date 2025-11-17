from __future__ import annotations

import httpx

from optimizer.notifiers.base import Notifier


class TelegramNotifier(Notifier):
    def __init__(self, bot_token: str, chat_id: str, enabled: bool) -> None:
        super().__init__(enabled and bool(bot_token and chat_id))
        self.bot_token = bot_token
        self.chat_id = chat_id

    async def _send_impl(self, message: str) -> None:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                json={"chat_id": self.chat_id, "text": message, "parse_mode": "Markdown"},
            )

