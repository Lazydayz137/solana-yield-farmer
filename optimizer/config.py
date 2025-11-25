from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class WalletConfig(BaseModel):
    name: str
    address: str
    private_key_path: str
    max_allocation_pct: float = Field(ge=0.0, le=1.0)


class StrategyConfig(BaseModel):
    harvest_interval_minutes: int = Field(default=180, ge=15)
    rotation_threshold_bps: int = Field(default=50, ge=10)
    min_apy: float = Field(default=5.0, ge=0.0)
    slippage_bps: int = Field(default=25, ge=1)
    target_vaults: List[str] = Field(default_factory=list)


class TelegramConfig(BaseModel):
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""


class DiscordConfig(BaseModel):
    enabled: bool = False
    webhook_url: str = ""


class NotificationConfig(BaseModel):
    telegram: TelegramConfig = TelegramConfig()
    discord: DiscordConfig = DiscordConfig()


class AnalyticsConfig(BaseModel):
    dashboard_refresh_seconds: int = Field(default=30, ge=5)


class NetworkConfig(BaseModel):
    rpc_endpoint: str
    commitment: str = "confirmed"


class DatabaseConfig(BaseModel):
    url: str = Field(default="sqlite+aiosqlite:///./optimizer.db")
    echo: bool = Field(default=False)


class AppConfig(BaseModel):
    network: NetworkConfig
    wallets: List[WalletConfig]
    strategy: StrategyConfig
    notifications: NotificationConfig = NotificationConfig()
    analytics: AnalyticsConfig = AnalyticsConfig()
    database: DatabaseConfig = DatabaseConfig()

    @classmethod
    def load(cls, path: str | Path) -> "AppConfig":
        """Load configuration from YAML file with environment variable substitution.

        Supports ${VAR_NAME} or ${VAR_NAME:default} syntax for env var substitution.

        Args:
            path: Path to configuration file

        Returns:
            Loaded and validated configuration
        """
        config_text = Path(path).read_text(encoding="utf-8")

        # Substitute environment variables
        config_text = cls._substitute_env_vars(config_text)

        data = yaml.safe_load(config_text)
        return cls(**data)

    @staticmethod
    def _substitute_env_vars(text: str) -> str:
        """Substitute ${VAR} or ${VAR:default} with environment variable values.

        Args:
            text: Text with env var placeholders

        Returns:
            Text with substituted values
        """
        pattern = re.compile(r'\$\{([^}:]+)(?::([^}]+))?\}')

        def replace(match):
            var_name = match.group(1)
            default_value = match.group(2) if match.group(2) is not None else ""
            return os.getenv(var_name, default_value)

        return pattern.sub(replace, text)


__all__ = ["AppConfig", "WalletConfig", "StrategyConfig", "NotificationConfig"]

