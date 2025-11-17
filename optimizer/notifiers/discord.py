from __future__ import annotations

import httpx

from optimizer.notifiers.base import Notifier


class DiscordNotifier(Notifier):
    def __init__(self, webhook_url: str, enabled: bool) -> None:
        super().__init__(enabled and bool(webhook_url))
        self.webhook_url = webhook_url

    async def _send_impl(self, message: str) -> None:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(self.webhook_url, json={"content": message})

