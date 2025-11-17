from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field


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


class AppConfig(BaseModel):
    network: NetworkConfig
    wallets: List[WalletConfig]
    strategy: StrategyConfig
    notifications: NotificationConfig = NotificationConfig()
    analytics: AnalyticsConfig = AnalyticsConfig()

    @classmethod
    def load(cls, path: str | Path) -> "AppConfig":
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return cls(**data)


__all__ = ["AppConfig", "WalletConfig", "StrategyConfig", "NotificationConfig"]

