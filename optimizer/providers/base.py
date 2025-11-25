from __future__ import annotations

import abc
import logging
import random
import time
from typing import Dict, List, Optional, Tuple

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from optimizer.models import Vault

LOGGER = logging.getLogger("optimizer.providers")


class VaultProvider(abc.ABC):
    """Base class that every Solana DEX/LP integration must inherit."""

    name: str
    cache_ttl_seconds: int = 30  # Default 30s cache

    def __init__(self, session: Optional[aiohttp.ClientSession] = None) -> None:
        self.session = session
        self.random = random.Random(hash(self.name) & 0xFFFF)
        self._cache: Dict[str, Tuple[List[Vault], float]] = {}
        self.logger = logging.getLogger(f"optimizer.providers.{self.name.lower()}")

    async def fetch_vaults(self, use_cache: bool = True) -> List[Vault]:
        """Fetch vaults with caching support.

        Args:
            use_cache: Whether to use cached data if available

        Returns:
            List of vaults
        """
        cache_key = "vaults"
        if use_cache and cache_key in self._cache:
            vaults, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self.cache_ttl_seconds:
                self.logger.debug("Returning cached vaults (age: %.1fs)", time.time() - timestamp)
                return vaults

        try:
            vaults = await self._fetch_vaults_impl()
            self._cache[cache_key] = (vaults, time.time())
            self.logger.info("Fetched %d vaults", len(vaults))
            return vaults
        except Exception as e:
            self.logger.error("Failed to fetch vaults: %s", e)
            # Return stale cache if available
            if cache_key in self._cache:
                vaults, timestamp = self._cache[cache_key]
                self.logger.warning("Returning stale cached data (age: %.1fs)", time.time() - timestamp)
                return vaults
            raise

    @abc.abstractmethod
    async def _fetch_vaults_impl(self) -> List[Vault]:
        """Actual implementation - subclasses implement this.

        Returns:
            List of vaults
        """

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, TimeoutError)),
    )
    async def _get_json(self, url: str, timeout: int = 10) -> dict:
        """Make HTTP GET request with retry logic.

        Args:
            url: URL to fetch
            timeout: Request timeout in seconds

        Returns:
            JSON response as dict
        """
        if self.session:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                resp.raise_for_status()
                return await resp.json()
        else:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                    resp.raise_for_status()
                    return await resp.json()

    def _mock_vault(
        self, symbol: str, apy: float, tvl: float, fee_bps: int, url: str,
        pool_address: Optional[str] = None, token_a: Optional[str] = None,
        token_b: Optional[str] = None
    ) -> Vault:
        """Create a mock vault for testing."""
        return Vault(
            name=symbol,
            platform=self.name,
            apy=apy,
            tvl_usd=tvl,
            fee_bps=fee_bps,
            volatility_score=self.random.uniform(0.2, 0.8),
            liquidity_score=self.random.uniform(0.5, 1.0),
            url=url,
            pool_address=pool_address,
            token_a=token_a,
            token_b=token_b,
        )

