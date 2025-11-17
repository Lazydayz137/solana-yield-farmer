from __future__ import annotations

import asyncio
from typing import List

from optimizer.models import Vault
from optimizer.providers.base import VaultProvider


class OrcaProvider(VaultProvider):
    name = "Orca"

    async def fetch_vaults(self) -> List[Vault]:
        await asyncio.sleep(0.05)
        return [
            self._mock_vault("mSOL-USDC", 12.4, 63_000_000, 14, "https://www.orca.so"),
            self._mock_vault("USDC-USDT", 7.2, 80_000_000, 8, "https://www.orca.so"),
            self._mock_vault("HNT-SOL", 29.7, 6_500_000, 28, "https://www.orca.so"),
        ]

