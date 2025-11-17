from __future__ import annotations

import abc
import random
from typing import List

from optimizer.models import Vault


class VaultProvider(abc.ABC):
    """Base class that every Solana DEX/LP integration must inherit."""

    name: str

    def __init__(self) -> None:
        self.random = random.Random(hash(self.name) & 0xFFFF)

    @abc.abstractmethod
    async def fetch_vaults(self) -> List[Vault]:
        """Return the latest vault metrics."""

    def _mock_vault(
        self, symbol: str, apy: float, tvl: float, fee_bps: int, url: str
    ) -> Vault:
        return Vault(
            name=symbol,
            platform=self.name,
            apy=apy,
            tvl_usd=tvl,
            fee_bps=fee_bps,
            volatility_score=self.random.uniform(0.2, 0.8),
            liquidity_score=self.random.uniform(0.5, 1.0),
            url=url,
        )

