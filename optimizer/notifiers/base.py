from __future__ import annotations

import abc
from typing import Protocol


class Notifier(abc.ABC):
    """Simple interface for alert backends."""

    enabled: bool

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    async def send(self, message: str) -> None:
        if not self.enabled:
            return
        await self._send_impl(message)

    @abc.abstractmethod
    async def _send_impl(self, message: str) -> None:
        """Subclass transports implement this."""

