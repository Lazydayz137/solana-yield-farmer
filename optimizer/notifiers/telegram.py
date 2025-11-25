from __future__ import annotations

import logging
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from optimizer.notifiers.base import Notifier

LOGGER = logging.getLogger("optimizer.notifiers.telegram")


class TelegramNotifier(Notifier):
    def __init__(self, bot_token: str, chat_id: str, enabled: bool) -> None:
        super().__init__(enabled and bool(bot_token and chat_id))
        self.bot_token = bot_token
        self.chat_id = chat_id

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True,
    )
    async def _send_impl(self, message: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                    json={"chat_id": self.chat_id, "text": message, "parse_mode": "Markdown"},
                )
                response.raise_for_status()
                LOGGER.debug("Telegram notification sent successfully")
        except httpx.HTTPStatusError as e:
            LOGGER.error("Telegram API returned error %d: %s", e.response.status_code, e.response.text)
            raise
        except httpx.HTTPError as e:
            LOGGER.error("Telegram notification failed: %s", e)
            raise
        except Exception as e:
            LOGGER.error("Unexpected error sending Telegram notification: %s", e)
            raise

