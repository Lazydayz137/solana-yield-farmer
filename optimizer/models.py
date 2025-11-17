from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


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


@dataclass(slots=True)
class VaultPosition:
    wallet: str
    vault: Vault
    amount_usd: float
    deposited_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def accrued_yield(self) -> float:
        days = (datetime.utcnow() - self.deposited_at).total_seconds() / 86400
        return self.amount_usd * (self.vault.apy / 100) * (days / 365)


__all__ = ["Vault", "VaultPosition"]

