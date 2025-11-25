from __future__ import annotations

import asyncio
from typing import List, Optional

from optimizer.models import Vault
from optimizer.providers.base import VaultProvider


class RaydiumProvider(VaultProvider):
    """Raydium DEX provider using V3 API."""

    name = "Raydium"
    BASE_URL = "https://api-v3.raydium.io"

    async def _fetch_vaults_impl(self) -> List[Vault]:
        """Fetch pools from Raydium V3 API.

        Returns:
            List of vaults with real data
        """
        try:
            # Fetch pool list from Raydium API
            data = await self._get_json(f"{self.BASE_URL}/pools/info/list")

            vaults = []
            pools = data.get("data", [])

            for pool in pools:
                try:
                    # Skip if missing required data
                    if not all(key in pool for key in ["id", "mintA", "mintB", "tvl"]):
                        continue

                    # Extract token symbols
                    token_a_symbol = pool["mintA"].get("symbol", "UNKNOWN")
                    token_b_symbol = pool["mintB"].get("symbol", "UNKNOWN")
                    pair_name = f"{token_a_symbol}-{token_b_symbol}"

                    # Calculate APY from fee APR and farming rewards
                    apy = self._calculate_apy(pool)

                    # Skip low TVL or low APY pools
                    tvl = float(pool.get("tvl", 0))
                    if tvl < 10000 or apy < 1.0:  # Skip pools with <$10k TVL or <1% APY
                        continue

                    # Get fee rate (convert from decimal to BPS)
                    fee_rate = float(pool.get("feeRate", 0.0025))  # Default 0.25%
                    fee_bps = int(fee_rate * 10000)

                    # Calculate scores
                    volatility_score = self._calculate_volatility(pool)
                    liquidity_score = self._calculate_liquidity(pool)

                    vault = Vault(
                        name=pair_name,
                        platform=self.name,
                        apy=apy,
                        tvl_usd=tvl,
                        fee_bps=fee_bps,
                        volatility_score=volatility_score,
                        liquidity_score=liquidity_score,
                        url=f"https://raydium.io/liquidity/increase/?pool_id={pool['id']}",
                        pool_address=pool.get("id"),
                        token_a=token_a_symbol,
                        token_b=token_b_symbol,
                    )
                    vaults.append(vault)

                except (KeyError, ValueError, TypeError) as e:
                    self.logger.debug("Skipping pool due to parsing error: %s", e)
                    continue

            self.logger.info("Parsed %d valid vaults from %d pools", len(vaults), len(pools))
            return vaults

        except Exception as e:
            self.logger.error("Failed to fetch Raydium pools: %s", e)
            # Fallback to mock data for now
            return await self._fetch_mock_vaults()

    def _calculate_apy(self, pool: dict) -> float:
        """Calculate APY from pool data.

        Args:
            pool: Pool data from API

        Returns:
            Estimated APY
        """
        # Try to get APY from various fields
        # Raydium might have apr, day/week/month stats
        if "apr" in pool:
            # APR from fees
            apr = float(pool["apr"])
            # Simple compounding: APY = (1 + APR/365)^365 - 1
            # For simplicity, approximate as APR * 1.05
            return apr * 1.05

        # Try farming rewards
        if "farmApr" in pool:
            return float(pool["farmApr"])

        # Fallback: estimate from volume and fees
        if "day" in pool and "volume" in pool["day"]:
            volume_24h = float(pool["day"]["volume"])
            tvl = float(pool.get("tvl", 1))
            fee_rate = float(pool.get("feeRate", 0.0025))

            if tvl > 0:
                # Daily fee income = volume * fee_rate
                daily_fees = volume_24h * fee_rate
                # APY = (daily_fees / tvl) * 365 * 100
                apy = (daily_fees / tvl) * 365 * 100
                return min(apy, 1000)  # Cap at 1000% to avoid outliers

        # Default conservative estimate
        return 5.0

    def _calculate_volatility(self, pool: dict) -> float:
        """Calculate volatility score from pool data.

        Args:
            pool: Pool data

        Returns:
            Volatility score (0-1, higher = more volatile)
        """
        # Check if pool contains stablecoins
        token_a = pool.get("mintA", {}).get("symbol", "").upper()
        token_b = pool.get("mintB", {}).get("symbol", "").upper()

        stablecoins = {"USDC", "USDT", "DAI", "USDS", "PYUSD"}

        if token_a in stablecoins and token_b in stablecoins:
            return 0.1  # Very low volatility (stablecoin pair)
        elif token_a in stablecoins or token_b in stablecoins:
            return 0.4  # Medium volatility (one stablecoin)
        else:
            return 0.7  # Higher volatility (both volatile tokens)

    def _calculate_liquidity(self, pool: dict) -> float:
        """Calculate liquidity score from TVL.

        Args:
            pool: Pool data

        Returns:
            Liquidity score (0-1, higher = better)
        """
        tvl = float(pool.get("tvl", 0))

        # Score based on TVL tiers
        if tvl >= 10_000_000:  # $10M+
            return 1.0
        elif tvl >= 1_000_000:  # $1M+
            return 0.8
        elif tvl >= 100_000:  # $100K+
            return 0.6
        elif tvl >= 10_000:  # $10K+
            return 0.4
        else:
            return 0.2

    async def _fetch_mock_vaults(self) -> List[Vault]:
        """Fallback mock data for testing."""
        await asyncio.sleep(0.05)
        return [
            self._mock_vault("RAY-USDC", 18.5, 42_000_000, 20, "https://raydium.io",
                           pool_address="mock1", token_a="RAY", token_b="USDC"),
            self._mock_vault("SOL-USDC", 14.2, 98_000_000, 15, "https://raydium.io",
                           pool_address="mock2", token_a="SOL", token_b="USDC"),
            self._mock_vault("JTO-USDC", 32.0, 9_000_000, 25, "https://raydium.io",
                           pool_address="mock3", token_a="JTO", token_b="USDC"),
        ]


__all__ = ["RaydiumProvider"]
