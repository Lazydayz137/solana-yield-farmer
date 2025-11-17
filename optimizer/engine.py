from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List

from optimizer.analytics.dashboard import DashboardSnapshot, render_dashboard
from optimizer.config import AppConfig
from optimizer.models import Vault, VaultPosition
from optimizer.notifiers.discord import DiscordNotifier
from optimizer.notifiers.telegram import TelegramNotifier
from optimizer.providers.meteora import MeteoraProvider
from optimizer.providers.orca import OrcaProvider
from optimizer.providers.raydium import RaydiumProvider

LOGGER = logging.getLogger("optimizer.engine")


class OptimizerEngine:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.providers = [RaydiumProvider(), MeteoraProvider(), OrcaProvider()]
        self.telegram = TelegramNotifier(
            config.notifications.telegram.bot_token,
            config.notifications.telegram.chat_id,
            config.notifications.telegram.enabled,
        )
        self.discord = DiscordNotifier(
            config.notifications.discord.webhook_url,
            config.notifications.discord.enabled,
        )
        self.positions: Dict[str, VaultPosition] = {}
        self._last_harvest = datetime.utcnow() - timedelta(
            minutes=config.strategy.harvest_interval_minutes
        )

    async def sync_vaults(self) -> List[Vault]:
        vaults: List[Vault] = []
        for provider in self.providers:
            vaults.extend(await provider.fetch_vaults())
        LOGGER.info("Fetched %s vaults", len(vaults))
        return vaults

    async def maybe_harvest(self) -> List[VaultPosition]:
        now = datetime.utcnow()
        if now - self._last_harvest < timedelta(minutes=self.config.strategy.harvest_interval_minutes):
            return []
        self._last_harvest = now
        harvested = []
        for pos in self.positions.values():
            yield_usd = pos.accrued_yield
            harvested.append(pos)
            LOGGER.info("Harvested %.2f USD from %s", yield_usd, pos.vault.name)
        if harvested:
            await self._notify(f"Harvested {len(harvested)} vaults at {now.isoformat()}")
        return harvested

    async def rebalance(self, vaults: List[Vault]) -> None:
        if not vaults:
            return
        vaults = [v for v in vaults if v.name in self.config.strategy.target_vaults or not self.config.strategy.target_vaults]
        if not vaults:
            return
        best = max(vaults, key=lambda v: v.apy)
        target_amount = sum(w.max_allocation_pct for w in self.config.wallets)
        allocation = target_amount * 100_000  # mock capital pool

        current = self.positions.get(best.name)
        if current and abs(current.vault.apy - best.apy) < self.config.strategy.rotation_threshold_bps / 100:
            return

        self.positions[best.name] = VaultPosition(wallet=self.config.wallets[0].name, vault=best, amount_usd=allocation)
        await self._notify(
            f"Rotated capital into {best.name} on {best.platform} (APY {best.apy:.2f}%)"
        )

    async def render(self, vaults: List[Vault]) -> None:
        snapshot = DashboardSnapshot(vaults=vaults, positions=list(self.positions.values()))
        render_dashboard(snapshot)

    async def run_once(self) -> None:
        vaults = await self.sync_vaults()
        await self.maybe_harvest()
        await self.rebalance(vaults)
        await self.render(vaults)

    async def serve(self) -> None:
        while True:
            await self.run_once()
            await asyncio.sleep(self.config.analytics.dashboard_refresh_seconds)

    async def _notify(self, message: str) -> None:
        await asyncio.gather(self.telegram.send(message), self.discord.send(message))


__all__ = ["OptimizerEngine"]

