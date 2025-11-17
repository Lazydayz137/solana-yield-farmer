from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from rich.console import Console
from rich.table import Table

from optimizer.models import VaultPosition, Vault


console = Console()


@dataclass
class DashboardSnapshot:
    vaults: List[Vault]
    positions: List[VaultPosition]

    @property
    def total_tvl(self) -> float:
        return sum(v.tvl_usd for v in self.vaults)

    @property
    def allocated(self) -> float:
        return sum(p.amount_usd for p in self.positions)

    @property
    def blended_apy(self) -> float:
        if not self.positions:
            return 0.0
        weighted = sum(p.amount_usd * p.vault.apy for p in self.positions)
        return weighted / self.allocated


def render_dashboard(snapshot: DashboardSnapshot) -> None:
    table = Table(title="Solana Yield Farming Overview", show_lines=True)
    table.add_column("Vault", justify="left")
    table.add_column("Platform")
    table.add_column("APY %", justify="right")
    table.add_column("TVL (USD)", justify="right")
    table.add_column("Liquidity", justify="right")
    table.add_column("Volatility", justify="right")

    for vault in sorted(snapshot.vaults, key=lambda v: v.apy, reverse=True):
        table.add_row(
            vault.name,
            vault.platform,
            f"{vault.apy:.2f}",
            f"{vault.tvl_usd:,.0f}",
            f"{vault.liquidity_score:.2f}",
            f"{vault.volatility_score:.2f}",
        )

    console.print(table)
    console.print(
        f"[bold cyan]Allocated:[/] ${snapshot.allocated:,.2f} | "
        f"[bold cyan]Total TVL tracked:[/] ${snapshot.total_tvl:,.0f} | "
        f"[bold cyan]Blended APY:[/] {snapshot.blended_apy:.2f}%"
    )

