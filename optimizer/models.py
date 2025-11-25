from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass(slots=True)
class Vault:
    name: str
    platform: str
    apy: float
    tvl_usd: float
    fee_bps: int
    volatility_score: float
    liquidity_score: float
    url: str
    pool_address: Optional[str] = None
    token_a: Optional[str] = None
    token_b: Optional[str] = None


@dataclass(slots=True)
class VaultPosition:
    wallet: str
    vault: Vault
    amount_usd: float
    deposited_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_harvest: Optional[datetime] = None
    total_harvested_usd: float = 0.0

    @property
    def accrued_yield(self) -> float:
        """Calculate yield accrued since last harvest or deposit."""
        start_time = self.last_harvest or self.deposited_at
        days = (datetime.now(timezone.utc) - start_time).total_seconds() / 86400
        return self.amount_usd * (self.vault.apy / 100) * (days / 365)


__all__ = ["Vault", "VaultPosition"]

