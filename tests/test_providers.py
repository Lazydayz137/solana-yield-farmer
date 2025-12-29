"""Tests for vault providers."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp

from optimizer.providers.raydium import RaydiumProvider
from optimizer.providers.meteora import MeteoraProvider
from optimizer.providers.orca import OrcaProvider
from optimizer.models import Vault


@pytest.mark.asyncio
async def test_raydium_provider_caching():
    """Test Raydium provider caching mechanism."""
    provider = RaydiumProvider()

    # Mock the API response
    mock_response = {
        "data": [
            {
                "id": "test123",
                "mintA": {"symbol": "SOL"},
                "mintB": {"symbol": "USDC"},
                "tvl": 1000000,
                "apr": 15.5,
                "feeRate": 0.0025,
            }
        ]
    }

    with patch.object(provider, '_get_json', new=AsyncMock(return_value=mock_response)):
        # First call should fetch from API
        vaults1 = await provider.fetch_vaults(use_cache=True)
        assert len(vaults1) > 0

        # Second call should use cache (within TTL)
        vaults2 = await provider.fetch_vaults(use_cache=True)
        assert vaults1 == vaults2

        # Verify _get_json was only called once (cached)
        assert provider._get_json.call_count == 1


@pytest.mark.asyncio
async def test_raydium_provider_api_parsing():
    """Test Raydium API response parsing."""
    provider = RaydiumProvider()

    mock_response = {
        "data": [
            {
                "id": "pool1",
                "mintA": {"symbol": "SOL"},
                "mintB": {"symbol": "USDC"},
                "tvl": 5000000,
                "apr": 20.0,
                "feeRate": 0.0025,
            },
            {
                "id": "pool2",
                "mintA": {"symbol": "BONK"},
                "mintB": {"symbol": "USDC"},
                "tvl": 500,  # Low TVL, should be filtered
                "apr": 50.0,
                "feeRate": 0.003,
            }
        ]
    }

    with patch.object(provider, '_get_json', new=AsyncMock(return_value=mock_response)):
        vaults = await provider.fetch_vaults(use_cache=False)

        # Should only include high TVL pool
        assert len(vaults) == 1
        assert vaults[0].name == "SOL-USDC"
        assert vaults[0].tvl_usd == 5000000
        assert vaults[0].platform == "Raydium"


@pytest.mark.asyncio
async def test_meteora_provider_fallback():
    """Test Meteora provider fallback to mock data on API failure."""
    provider = MeteoraProvider()

    # Mock API failure
    with patch.object(provider, '_get_json', side_effect=aiohttp.ClientError("API error")):
        vaults = await provider.fetch_vaults(use_cache=False)

        # Should return mock data
        assert len(vaults) > 0
        assert all(v.platform == "Meteora" for v in vaults)


@pytest.mark.asyncio
async def test_orca_provider_known_pools():
    """Test Orca provider returns known pools."""
    provider = OrcaProvider()

    vaults = await provider.fetch_vaults()

    assert len(vaults) > 0
    assert all(v.platform == "Orca" for v in vaults)
    assert any(v.name == "SOL-USDC" for v in vaults)
    assert any(v.name == "USDC-USDT" for v in vaults)


@pytest.mark.asyncio
async def test_provider_volatility_scoring():
    """Test volatility scoring logic."""
    provider = RaydiumProvider()

    mock_response = {
        "data": [
            {
                "id": "pool1",
                "mintA": {"symbol": "USDC"},
                "mintB": {"symbol": "USDT"},
                "tvl": 1000000,
                "apr": 5.0,
                "feeRate": 0.0001,
            },
            {
                "id": "pool2",
                "mintA": {"symbol": "SOL"},
                "mintB": {"symbol": "USDC"},
                "tvl": 1000000,
                "apr": 15.0,
                "feeRate": 0.0025,
            },
            {
                "id": "pool3",
                "mintA": {"symbol": "BONK"},
                "mintB": {"symbol": "JUP"},
                "tvl": 1000000,
                "apr": 50.0,
                "feeRate": 0.003,
            }
        ]
    }

    with patch.object(provider, '_get_json', new=AsyncMock(return_value=mock_response)):
        vaults = await provider.fetch_vaults(use_cache=False)

        # Find each vault
        stablecoin_pair = next(v for v in vaults if v.name == "USDC-USDT")
        stable_volatile = next(v for v in vaults if v.name == "SOL-USDC")
        volatile_pair = next(v for v in vaults if v.name == "BONK-JUP")

        # Stablecoin pairs should have lowest volatility
        assert stablecoin_pair.volatility_score < stable_volatile.volatility_score
        assert stable_volatile.volatility_score < volatile_pair.volatility_score


@pytest.mark.asyncio
async def test_provider_liquidity_scoring():
    """Test liquidity scoring based on TVL."""
    provider = RaydiumProvider()

    mock_response = {
        "data": [
            {
                "id": "pool1",
                "mintA": {"symbol": "SOL"},
                "mintB": {"symbol": "USDC"},
                "tvl": 50000000,  # $50M
                "apr": 15.0,
                "feeRate": 0.0025,
            },
            {
                "id": "pool2",
                "mintA": {"symbol": "BONK"},
                "mintB": {"symbol": "USDC"},
                "tvl": 500000,  # $500K
                "apr": 30.0,
                "feeRate": 0.003,
            }
        ]
    }

    with patch.object(provider, '_get_json', new=AsyncMock(return_value=mock_response)):
        vaults = await provider.fetch_vaults(use_cache=False)

        high_tvl = next(v for v in vaults if v.tvl_usd == 50000000)
        medium_tvl = next(v for v in vaults if v.tvl_usd == 500000)

        # Higher TVL should have better liquidity score
        assert high_tvl.liquidity_score > medium_tvl.liquidity_score


@pytest.mark.asyncio
async def test_provider_stale_cache_fallback():
    """Test provider uses stale cache when API fails."""
    provider = RaydiumProvider()

    mock_response = {
        "data": [
            {
                "id": "pool1",
                "mintA": {"symbol": "SOL"},
                "mintB": {"symbol": "USDC"},
                "tvl": 1000000,
                "apr": 15.0,
                "feeRate": 0.0025,
            }
        ]
    }

    # First successful call
    with patch.object(provider, '_get_json', new=AsyncMock(return_value=mock_response)):
        vaults1 = await provider.fetch_vaults(use_cache=True)
        assert len(vaults1) > 0

    # Expire cache by setting TTL to 0
    provider.cache_ttl_seconds = 0

    # Second call fails but should return stale cache
    with patch.object(provider, '_get_json', side_effect=aiohttp.ClientError("API down")):
        vaults2 = await provider.fetch_vaults(use_cache=True)
        assert vaults2 == vaults1  # Should return same cached data


def test_provider_mock_vault_creation():
    """Test mock vault creation helper."""
    provider = RaydiumProvider()

    vault = provider._mock_vault(
        symbol="TEST-USDC",
        apy=25.5,
        tvl=1000000,
        fee_bps=30,
        url="https://example.com",
        pool_address="test123",
        token_a="TEST",
        token_b="USDC"
    )

    assert vault.name == "TEST-USDC"
    assert vault.platform == "Raydium"
    assert vault.apy == 25.5
    assert vault.tvl_usd == 1000000
    assert vault.fee_bps == 30
    assert vault.url == "https://example.com"
    assert vault.pool_address == "test123"
    assert vault.token_a == "TEST"
    assert vault.token_b == "USDC"
    assert 0 <= vault.volatility_score <= 1
    assert 0 <= vault.liquidity_score <= 1
