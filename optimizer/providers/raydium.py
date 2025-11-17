from __future__ import annotations

import asyncio
from typing import List

from optimizer.models import Vault
from optimizer.providers.base import VaultProvider


class RaydiumProvider(VaultProvider):
    name = "Raydium"

    async def fetch_vaults(self) -> List[Vault]:
        await asyncio.sleep(0.05)
        return [
            self._mock_vault("RAY-USDC", 18.5, 42_000_000, 20, "https://raydium.io"),
            self._mock_vault("SOL-USDC", 14.2, 98_000_000, 15, "https://raydium.io"),
            self._mock_vault("JTO-USDC", 32.0, 9_000_000, 25, "https://raydium.io"),
        ]

