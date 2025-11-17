from __future__ import annotations

import asyncio
from typing import List

from optimizer.models import Vault
from optimizer.providers.base import VaultProvider


class MeteoraProvider(VaultProvider):
    name = "Meteora"

    async def fetch_vaults(self) -> List[Vault]:
        await asyncio.sleep(0.05)
        return [
            self._mock_vault("SOL-USDT", 21.3, 55_000_000, 18, "https://beta.meteora.ag"),
            self._mock_vault("BONK-USDC", 45.8, 11_000_000, 30, "https://beta.meteora.ag"),
            self._mock_vault("JUP-USDC", 27.5, 25_000_000, 22, "https://beta.meteora.ag"),
        ]

