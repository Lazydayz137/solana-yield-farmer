from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
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
        self._last_harvest = datetime.now(timezone.utc) - timedelta(
            minutes=config.strategy.harvest_interval_minutes
        )

    async def sync_vaults(self) -> List[Vault]:
        """Fetch vaults from all providers concurrently."""
        try:
            results = await asyncio.gather(
                *[provider.fetch_vaults() for provider in self.providers],
                return_exceptions=True
            )
            vaults: List[Vault] = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    LOGGER.error("Provider %s failed: %s", self.providers[i].name, result)
                else:
                    vaults.extend(result)
            LOGGER.info("Fetched %s vaults from %s providers", len(vaults), len(self.providers))
            return vaults
        except Exception as e:
            LOGGER.error("Failed to sync vaults: %s", e)
            return []

    async def maybe_harvest(self) -> List[VaultPosition]:
        """Harvest positions if interval has elapsed."""
        now = datetime.now(timezone.utc)
        if now - self._last_harvest < timedelta(minutes=self.config.strategy.harvest_interval_minutes):
            return []
        self._last_harvest = now
        harvested = []
        for pos in self.positions.values():
            yield_usd = pos.accrued_yield
            if yield_usd > 0:
                pos.total_harvested_usd += yield_usd
                pos.last_harvest = now
                harvested.append(pos)
                LOGGER.info("Harvested %.2f USD from %s (total: %.2f)",
                           yield_usd, pos.vault.name, pos.total_harvested_usd)
        if harvested:
            total_yield = sum(p.accrued_yield for p in harvested)
            await self._notify(
                f"🌾 Harvested {len(harvested)} positions\n"
                f"Total yield: ${total_yield:,.2f}"
            )
        return harvested

    async def rebalance(self, vaults: List[Vault]) -> None:
        """Rebalance positions to highest APY vault if threshold met."""
        if not vaults:
            return

        # Filter by target vaults if specified
        filtered_vaults = [
            v for v in vaults
            if not self.config.strategy.target_vaults or v.name in self.config.strategy.target_vaults
        ]

        # Apply minimum APY filter
        filtered_vaults = [v for v in filtered_vaults if v.apy >= self.config.strategy.min_apy]

        if not filtered_vaults:
            LOGGER.warning("No vaults meet criteria (min APY: %.2f%%)", self.config.strategy.min_apy)
            return

        best = max(filtered_vaults, key=lambda v: v.apy)
        target_amount = sum(w.max_allocation_pct for w in self.config.wallets)
        allocation = target_amount * 100_000  # TODO: Replace with real wallet balance

        # Check if rotation is needed (BPS comparison fixed)
        current = self.positions.get(best.name)
        if current:
            apy_diff_bps = abs(current.vault.apy - best.apy) * 100  # Convert % to BPS
            if apy_diff_bps < self.config.strategy.rotation_threshold_bps:
                LOGGER.debug("APY difference %.2f BPS below threshold %d BPS",
                            apy_diff_bps, self.config.strategy.rotation_threshold_bps)
                return

        self.positions[best.name] = VaultPosition(
            wallet=self.config.wallets[0].name,
            vault=best,
            amount_usd=allocation
        )
        await self._notify(
            f"🔄 Rotated to {best.name} ({best.platform})\n"
            f"APY: {best.apy:.2f}% | TVL: ${best.tvl_usd:,.0f}"
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

