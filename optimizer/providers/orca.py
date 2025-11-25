from __future__ import annotations

import asyncio
from typing import List

from optimizer.models import Vault
from optimizer.providers.base import VaultProvider


class OrcaProvider(VaultProvider):
    """Orca Whirlpools provider."""

    name = "Orca"
    # Note: Orca doesn't have a public REST API for all pools
    # In production, you'd use the Whirlpools SDK or on-chain data
    # For now, we'll use a combination of known pools and fallback to mock

    async def _fetch_vaults_impl(self) -> List[Vault]:
        """Fetch Whirlpools from Orca.

        Note: This is a simplified implementation.
        Production should use @orca-so/whirlpools SDK with on-chain data.

        Returns:
            List of vaults
        """
        try:
            # Orca doesn't have a public pools API like Raydium
            # Would need to use Solana RPC + Whirlpools program
            # For now, return curated list of known high-TVL pools
            vaults = await self._fetch_known_pools()
            self.logger.info("Fetched %d known Orca pools", len(vaults))
            return vaults

        except Exception as e:
            self.logger.error("Failed to fetch Orca pools: %s", e)
            return await self._fetch_mock_vaults()

    async def _fetch_known_pools(self) -> List[Vault]:
        """Fetch known high-liquidity Orca pools.

        Returns:
            List of vaults
        """
        # Known Orca Whirlpool addresses and data
        # In production, fetch this from on-chain or a maintained registry
        known_pools = [
            {
                "name": "SOL-USDC",
                "address": "7qbRF6YsyGuLUVs6Y1q64bdVrfe4ZcUUz1JRdoVNUJnm",
                "token_a": "SOL",
                "token_b": "USDC",
                "apy": 12.4,
                "tvl": 63_000_000,
                "fee_bps": 14,
            },
            {
                "name": "USDC-USDT",
                "address": "4fuUiYxTQ6QCrdSq9ouBYcTM7bqSwYTSyLueGZLTy4T4",
                "token_a": "USDC",
                "token_b": "USDT",
                "apy": 7.2,
                "tvl": 80_000_000,
                "fee_bps": 8,
            },
            {
                "name": "mSOL-SOL",
                "address": "9vqYJjDUFecLL2xPUC4Rc7hyCtZ6iJ4mDiVZX7aFXoAe",
                "token_a": "mSOL",
                "token_b": "SOL",
                "apy": 8.5,
                "tvl": 45_000_000,
                "fee_bps": 10,
            },
            {
                "name": "ORCA-USDC",
                "address": "2p7nYbtPBgtmY69NsE8DAW6szpRJn7tQvDnqvoEWQvjY",
                "token_a": "ORCA",
                "token_b": "USDC",
                "apy": 18.3,
                "tvl": 12_000_000,
                "fee_bps": 20,
            },
        ]

        vaults = []
        for pool in known_pools:
            volatility_score = self._calculate_volatility(pool["token_a"], pool["token_b"])
            liquidity_score = self._calculate_liquidity(pool["tvl"])

            vault = Vault(
                name=pool["name"],
                platform=self.name,
                apy=pool["apy"],
                tvl_usd=pool["tvl"],
                fee_bps=pool["fee_bps"],
                volatility_score=volatility_score,
                liquidity_score=liquidity_score,
                url=f"https://www.orca.so/pools?pool={pool['address']}",
                pool_address=pool["address"],
                token_a=pool["token_a"],
                token_b=pool["token_b"],
            )
            vaults.append(vault)

        return vaults

    def _calculate_volatility(self, token_a: str, token_b: str) -> float:
        """Calculate volatility score from tokens."""
        stablecoins = {"USDC", "USDT", "DAI", "USDS", "PYUSD"}
        liquid_staking = {"mSOL", "stSOL", "jitoSOL"}

        token_a_upper = token_a.upper()
        token_b_upper = token_b.upper()

        # Stablecoin pairs
        if token_a_upper in stablecoins and token_b_upper in stablecoins:
            return 0.1

        # LST-SOL pairs (low volatility)
        if (token_a_upper in liquid_staking and token_b_upper == "SOL") or \
           (token_b_upper in liquid_staking and token_a_upper == "SOL"):
            return 0.2

        # One stablecoin
        if token_a_upper in stablecoins or token_b_upper in stablecoins:
            return 0.4

        # Both volatile
        return 0.7

    def _calculate_liquidity(self, tvl: float) -> float:
        """Calculate liquidity score from TVL."""
        if tvl >= 10_000_000:
            return 1.0
        elif tvl >= 1_000_000:
            return 0.8
        elif tvl >= 100_000:
            return 0.6
        else:
            return 0.4

    async def _fetch_mock_vaults(self) -> List[Vault]:
        """Fallback mock data."""
        await asyncio.sleep(0.05)
        return [
            self._mock_vault("mSOL-USDC", 12.4, 63_000_000, 14, "https://www.orca.so",
                           pool_address="mock1", token_a="mSOL", token_b="USDC"),
            self._mock_vault("USDC-USDT", 7.2, 80_000_000, 8, "https://www.orca.so",
                           pool_address="mock2", token_a="USDC", token_b="USDT"),
            self._mock_vault("HNT-SOL", 29.7, 6_500_000, 28, "https://www.orca.so",
                           pool_address="mock3", token_a="HNT", token_b="SOL"),
        ]


__all__ = ["OrcaProvider"]
