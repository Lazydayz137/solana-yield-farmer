"""Tests for configuration loading and validation."""
from pathlib import Path
import tempfile
import os
import pytest

from optimizer.config import AppConfig, WalletConfig, StrategyConfig


def test_load_basic_config():
    """Test loading a basic configuration file."""
    config_yaml = """
network:
  rpc_endpoint: https://api.mainnet-beta.solana.com
  commitment: confirmed

wallets:
  - name: test
    address: "11111111111111111111111111111111"
    private_key_path: /tmp/test.json
    max_allocation_pct: 1.0

strategy:
  harvest_interval_minutes: 60
  rotation_threshold_bps: 50
  min_apy: 5.0
  slippage_bps: 25
  target_vaults: []

notifications:
  telegram:
    enabled: false
    bot_token: ""
    chat_id: ""
  discord:
    enabled: false
    webhook_url: ""

analytics:
  dashboard_refresh_seconds: 30

database:
  url: sqlite+aiosqlite:///./test.db
  echo: false
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_yaml)
        config_path = f.name

    try:
        config = AppConfig.load(config_path)

        assert config.network.rpc_endpoint == "https://api.mainnet-beta.solana.com"
        assert config.network.commitment == "confirmed"
        assert len(config.wallets) == 1
        assert config.wallets[0].name == "test"
        assert config.strategy.harvest_interval_minutes == 60
        assert config.strategy.rotation_threshold_bps == 50
        assert config.database.url == "sqlite+aiosqlite:///./test.db"
    finally:
        os.unlink(config_path)


def test_env_var_substitution():
    """Test environment variable substitution in config."""
    config_yaml = """
network:
  rpc_endpoint: ${TEST_RPC_URL:https://default.example.com}
  commitment: confirmed

wallets:
  - name: test
    address: "${TEST_WALLET:11111111111111111111111111111111}"
    private_key_path: /tmp/test.json
    max_allocation_pct: 1.0

strategy:
  harvest_interval_minutes: 60
  rotation_threshold_bps: 50
  min_apy: 5.0
  slippage_bps: 25
  target_vaults: []
"""

    # Set environment variable
    os.environ['TEST_RPC_URL'] = 'https://custom.rpc.com'
    os.environ['TEST_WALLET'] = '22222222222222222222222222222222'

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_yaml)
        config_path = f.name

    try:
        config = AppConfig.load(config_path)

        assert config.network.rpc_endpoint == "https://custom.rpc.com"
        assert config.wallets[0].address == "22222222222222222222222222222222"
    finally:
        os.unlink(config_path)
        del os.environ['TEST_RPC_URL']
        del os.environ['TEST_WALLET']


def test_env_var_default():
    """Test environment variable default values."""
    config_yaml = """
network:
  rpc_endpoint: ${NONEXISTENT_VAR:https://default.example.com}
  commitment: confirmed

wallets:
  - name: test
    address: "11111111111111111111111111111111"
    private_key_path: /tmp/test.json
    max_allocation_pct: 1.0

strategy:
  harvest_interval_minutes: 60
  rotation_threshold_bps: 50
  min_apy: 5.0
  slippage_bps: 25
  target_vaults: []
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_yaml)
        config_path = f.name

    try:
        config = AppConfig.load(config_path)
        assert config.network.rpc_endpoint == "https://default.example.com"
    finally:
        os.unlink(config_path)


def test_strategy_validation():
    """Test strategy configuration validation."""
    # Test minimum harvest interval
    with pytest.raises(Exception):
        StrategyConfig(
            harvest_interval_minutes=10,  # Below minimum of 15
            rotation_threshold_bps=50,
            min_apy=5.0,
            slippage_bps=25,
        )

    # Test minimum rotation threshold
    with pytest.raises(Exception):
        StrategyConfig(
            harvest_interval_minutes=60,
            rotation_threshold_bps=5,  # Below minimum of 10
            min_apy=5.0,
            slippage_bps=25,
        )


def test_wallet_validation():
    """Test wallet configuration validation."""
    # Test max_allocation_pct range
    with pytest.raises(Exception):
        WalletConfig(
            name="test",
            address="11111111111111111111111111111111",
            private_key_path="/tmp/test.json",
            max_allocation_pct=1.5,  # Above maximum of 1.0
        )

    with pytest.raises(Exception):
        WalletConfig(
            name="test",
            address="11111111111111111111111111111111",
            private_key_path="/tmp/test.json",
            max_allocation_pct=-0.1,  # Below minimum of 0.0
        )


def test_config_defaults():
    """Test configuration default values."""
    config_yaml = """
network:
  rpc_endpoint: https://api.mainnet-beta.solana.com

wallets:
  - name: test
    address: "11111111111111111111111111111111"
    private_key_path: /tmp/test.json
    max_allocation_pct: 1.0

strategy:
  harvest_interval_minutes: 60
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_yaml)
        config_path = f.name

    try:
        config = AppConfig.load(config_path)

        # Check defaults
        assert config.network.commitment == "confirmed"
        assert config.strategy.rotation_threshold_bps == 50
        assert config.strategy.min_apy == 5.0
        assert config.strategy.slippage_bps == 25
        assert config.analytics.dashboard_refresh_seconds == 30
        assert config.database.url == "sqlite+aiosqlite:///./optimizer.db"
        assert config.notifications.telegram.enabled is False
    finally:
        os.unlink(config_path)
