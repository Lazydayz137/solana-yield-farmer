"""Tests for core models."""
from datetime import datetime, timezone, timedelta
import pytest

from optimizer.models import Vault, VaultPosition


def test_vault_creation():
    """Test Vault model creation."""
    vault = Vault(
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

    assert vault.name == "SOL-USDC"
    assert vault.platform == "Raydium"
    assert vault.apy == 15.5
    assert vault.tvl_usd == 10000000
    assert vault.fee_bps == 25
    assert vault.pool_address == "test123"


def test_vault_position_accrued_yield():
    """Test VaultPosition accrued yield calculation."""
    vault = Vault(
        name="SOL-USDC",
        platform="Raydium",
        apy=36.5,  # 36.5% APY for easy calculation (0.1% per day)
        tvl_usd=10000000,
        fee_bps=25,
        volatility_score=0.4,
        liquidity_score=0.9,
        url="https://raydium.io",
    )

    # Create position 10 days ago
    deposited_at = datetime.now(timezone.utc) - timedelta(days=10)
    position = VaultPosition(
        wallet="test",
        vault=vault,
        amount_usd=10000,
        deposited_at=deposited_at,
    )

    # Calculate expected yield: 10000 * (36.5/100) * (10/365) = ~100
    expected_yield = 10000 * (36.5 / 100) * (10 / 365)
    actual_yield = position.accrued_yield

    # Allow small floating point difference
    assert abs(actual_yield - expected_yield) < 0.01


def test_vault_position_harvest_tracking():
    """Test harvest tracking in VaultPosition."""
    vault = Vault(
        name="SOL-USDC",
        platform="Raydium",
        apy=36.5,
        tvl_usd=10000000,
        fee_bps=25,
        volatility_score=0.4,
        liquidity_score=0.9,
        url="https://raydium.io",
    )

    # Create position
    position = VaultPosition(
        wallet="test",
        vault=vault,
        amount_usd=10000,
        deposited_at=datetime.now(timezone.utc) - timedelta(days=10),
    )

    # Simulate harvest
    yield_amount = position.accrued_yield
    position.total_harvested_usd += yield_amount
    position.last_harvest = datetime.now(timezone.utc)

    assert position.total_harvested_usd > 0
    assert position.last_harvest is not None

    # Accrued yield should be near zero after harvest
    assert position.accrued_yield < 1  # Less than $1


def test_vault_position_multiple_harvests():
    """Test multiple harvests accumulate correctly."""
    vault = Vault(
        name="SOL-USDC",
        platform="Raydium",
        apy=36.5,
        tvl_usd=10000000,
        fee_bps=25,
        volatility_score=0.4,
        liquidity_score=0.9,
        url="https://raydium.io",
    )

    position = VaultPosition(
        wallet="test",
        vault=vault,
        amount_usd=10000,
        deposited_at=datetime.now(timezone.utc) - timedelta(days=5),
    )

    # First harvest
    yield1 = position.accrued_yield
    position.total_harvested_usd += yield1
    position.last_harvest = datetime.now(timezone.utc) - timedelta(days=3)

    # Second harvest (3 days later)
    yield2 = position.accrued_yield
    position.total_harvested_usd += yield2
    position.last_harvest = datetime.now(timezone.utc)

    # Total harvested should be sum of both
    expected_total = yield1 + yield2
    assert abs(position.total_harvested_usd - expected_total) < 0.01


def test_vault_optional_fields():
    """Test Vault optional fields default to None."""
    vault = Vault(
        name="SOL-USDC",
        platform="Raydium",
        apy=15.5,
        tvl_usd=10000000,
        fee_bps=25,
        volatility_score=0.4,
        liquidity_score=0.9,
        url="https://raydium.io",
    )

    assert vault.pool_address is None
    assert vault.token_a is None
    assert vault.token_b is None


def test_position_defaults():
    """Test VaultPosition default values."""
    vault = Vault(
        name="SOL-USDC",
        platform="Raydium",
        apy=15.5,
        tvl_usd=10000000,
        fee_bps=25,
        volatility_score=0.4,
        liquidity_score=0.9,
        url="https://raydium.io",
    )

    position = VaultPosition(
        wallet="test",
        vault=vault,
        amount_usd=10000,
    )

    assert position.last_harvest is None
    assert position.total_harvested_usd == 0.0
    assert position.deposited_at <= datetime.now(timezone.utc)
