"""Pytest configuration and fixtures."""
import pytest
import asyncio


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_vault():
    """Fixture providing a sample vault for testing."""
    from optimizer.models import Vault

    return Vault(
        name="SOL-USDC",
        platform="Raydium",
        apy=15.5,
        tvl_usd=10000000,
        fee_bps=25,
        volatility_score=0.4,
        liquidity_score=0.9,
        url="https://raydium.io",
        pool_address="test123",
        token_a="SOL",
        token_b="USDC",
    )


@pytest.fixture
def sample_position(sample_vault):
    """Fixture providing a sample position for testing."""
    from optimizer.models import VaultPosition
    from datetime import datetime, timezone

    return VaultPosition(
        wallet="test_wallet",
        vault=sample_vault,
        amount_usd=10000,
        deposited_at=datetime.now(timezone.utc),
    )
