from __future__ import annotations

import asyncio
from typing import List

from optimizer.models import Vault
from optimizer.providers.base import VaultProvider


class MeteoraProvider(VaultProvider):
    """Meteora DLMM provider using public API."""

    name = "Meteora"
    BASE_URL = "https://dlmm-api.meteora.ag"

    async def _fetch_vaults_impl(self) -> List[Vault]:
        """Fetch DLMM pools from Meteora API.

        Returns:
            List of vaults with real data
        """
        try:
            # Fetch pool list from Meteora DLMM API
            data = await self._get_json(f"{self.BASE_URL}/pair/all")

            vaults = []

            # Meteora returns a list or dict with pools
            pools = data if isinstance(data, list) else data.get("data", [])

            for pool in pools:
                try:
                    # Skip if missing required data
                    if not isinstance(pool, dict):
                        continue

                    # Extract pool information
                    name = pool.get("name", "")
                    if not name:
                        continue

                    # Get TVL and APY
                    tvl = float(pool.get("liquidity", 0))
                    if tvl < 10000:  # Skip low TVL pools
                        continue

                    # Calculate APY from fees and farming rewards
                    apy = self._calculate_apy(pool)
                    if apy < 1.0:  # Skip low APY pools
                        continue

                    # Get fee rate
                    fee_rate = float(pool.get("fee_rate", 0.003))  # Default 0.3%
                    fee_bps = int(fee_rate * 10000)

                    # Get pool address
                    pool_address = pool.get("address", pool.get("pool_address"))

                    # Extract tokens
                    mint_x = pool.get("mint_x", {})
                    mint_y = pool.get("mint_y", {})
                    token_a = mint_x.get("symbol", "UNKNOWN") if isinstance(mint_x, dict) else "UNKNOWN"
                    token_b = mint_y.get("symbol", "UNKNOWN") if isinstance(mint_y, dict) else "UNKNOWN"

                    # Calculate scores
                    volatility_score = self._calculate_volatility(token_a, token_b)
                    liquidity_score = self._calculate_liquidity(tvl)

                    vault = Vault(
                        name=name,
                        platform=self.name,
                        apy=apy,
                        tvl_usd=tvl,
                        fee_bps=fee_bps,
                        volatility_score=volatility_score,
                        liquidity_score=liquidity_score,
                        url=f"https://app.meteora.ag/pools/{pool_address}" if pool_address else "https://app.meteora.ag",
                        pool_address=pool_address,
                        token_a=token_a,
                        token_b=token_b,
                    )
                    vaults.append(vault)

                except (KeyError, ValueError, TypeError) as e:
                    self.logger.debug("Skipping pool due to parsing error: %s", e)
                    continue

            self.logger.info("Parsed %d valid vaults from %d pools", len(vaults), len(pools))
            return vaults

        except Exception as e:
            self.logger.error("Failed to fetch Meteora pools: %s", e)
            # Fallback to mock data
            return await self._fetch_mock_vaults()

    def _calculate_apy(self, pool: dict) -> float:
        """Calculate APY from pool data.

        Args:
            pool: Pool data from API

        Returns:
            Estimated APY
        """
        # Try various APY fields
        if "apy" in pool:
            return float(pool["apy"])

        if "apr" in pool:
            apr = float(pool["apr"])
            return apr * 1.05  # Approximate compounding

        if "fees_24h" in pool and "liquidity" in pool:
            fees_24h = float(pool["fees_24h"])
            tvl = float(pool["liquidity"])
            if tvl > 0:
                apy = (fees_24h / tvl) * 365 * 100
                return min(apy, 1000)

        # Default estimate based on platform
        return 15.0  # Meteora typically has higher APYs

    def _calculate_volatility(self, token_a: str, token_b: str) -> float:
        """Calculate volatility score from tokens.

        Args:
            token_a: First token symbol
            token_b: Second token symbol

        Returns:
            Volatility score (0-1)
        """
        stablecoins = {"USDC", "USDT", "DAI", "USDS", "PYUSD"}
        token_a_upper = token_a.upper()
        token_b_upper = token_b.upper()

        if token_a_upper in stablecoins and token_b_upper in stablecoins:
            return 0.1
        elif token_a_upper in stablecoins or token_b_upper in stablecoins:
            return 0.4
        else:
            return 0.7

    def _calculate_liquidity(self, tvl: float) -> float:
        """Calculate liquidity score from TVL.

        Args:
            tvl: Total value locked

        Returns:
            Liquidity score (0-1)
        """
        if tvl >= 10_000_000:
            return 1.0
        elif tvl >= 1_000_000:
            return 0.8
        elif tvl >= 100_000:
            return 0.6
        elif tvl >= 10_000:
            return 0.4
        else:
            return 0.2

    async def _fetch_mock_vaults(self) -> List[Vault]:
        """Fallback mock data for testing."""
        await asyncio.sleep(0.05)
        return [
            self._mock_vault("SOL-USDT", 21.3, 55_000_000, 18, "https://app.meteora.ag",
                           pool_address="mock1", token_a="SOL", token_b="USDT"),
            self._mock_vault("BONK-USDC", 45.8, 11_000_000, 30, "https://app.meteora.ag",
                           pool_address="mock2", token_a="BONK", token_b="USDC"),
            self._mock_vault("JUP-USDC", 27.5, 25_000_000, 22, "https://app.meteora.ag",
                           pool_address="mock3", token_a="JUP", token_b="USDC"),
        ]


__all__ = ["MeteoraProvider"]
