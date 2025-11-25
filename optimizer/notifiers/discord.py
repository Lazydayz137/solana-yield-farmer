from __future__ import annotations

import logging
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from optimizer.notifiers.base import Notifier

LOGGER = logging.getLogger("optimizer.notifiers.discord")


class DiscordNotifier(Notifier):
    def __init__(self, webhook_url: str, enabled: bool) -> None:
        super().__init__(enabled and bool(webhook_url))
        self.webhook_url = webhook_url

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True,
    )
    async def _send_impl(self, message: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(self.webhook_url, json={"content": message})
                response.raise_for_status()
                LOGGER.debug("Discord notification sent successfully")
        except httpx.HTTPStatusError as e:
            LOGGER.error("Discord webhook returned error %d: %s", e.response.status_code, e.response.text)
            raise
        except httpx.HTTPError as e:
            LOGGER.error("Discord notification failed: %s", e)
            raise
        except Exception as e:
            LOGGER.error("Unexpected error sending Discord notification: %s", e)
            raise

