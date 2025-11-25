from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.types import TokenAccountOpts

from optimizer.config import WalletConfig

LOGGER = logging.getLogger("optimizer.wallet")


class WalletManager:
    """Manages wallet keypairs and balance queries."""

    def __init__(self, config: WalletConfig, rpc_client: AsyncClient) -> None:
        self.config = config
        self.rpc = rpc_client
        self._keypair: Optional[Keypair] = None

    def load_keypair(self) -> Keypair:
        """Load keypair from file securely.

        Returns:
            Keypair: Loaded Solana keypair

        Raises:
            FileNotFoundError: If keypair file doesn't exist
            ValueError: If keypair file is invalid
        """
        if self._keypair:
            return self._keypair

        path = Path(self.config.private_key_path)
        if not path.exists():
            raise FileNotFoundError(f"Keypair file not found: {path}")

        try:
            with open(path, "r") as f:
                secret_key = json.load(f)

            if not isinstance(secret_key, list) or len(secret_key) != 64:
                raise ValueError("Invalid keypair format: expected array of 64 bytes")

            self._keypair = Keypair.from_bytes(bytes(secret_key))
            LOGGER.info("Loaded keypair for wallet %s", self.config.name)
            return self._keypair

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in keypair file: {e}")
        except Exception as e:
            raise ValueError(f"Failed to load keypair: {e}")

    @property
    def pubkey(self) -> Pubkey:
        """Get the public key of the wallet."""
        if not self._keypair:
            self.load_keypair()
        return self._keypair.pubkey()

    async def get_sol_balance(self) -> float:
        """Get SOL balance in lamports converted to SOL.

        Returns:
            float: SOL balance
        """
        try:
            response = await self.rpc.get_balance(self.pubkey)
            if response.value is not None:
                return response.value / 1e9  # Convert lamports to SOL
            return 0.0
        except Exception as e:
            LOGGER.error("Failed to get SOL balance for %s: %s", self.config.name, e)
            return 0.0

    async def get_token_balance(self, mint: Pubkey) -> float:
        """Get SPL token balance for a specific mint.

        Args:
            mint: Token mint address

        Returns:
            float: Token balance
        """
        try:
            opts = TokenAccountOpts(mint=mint)
            response = await self.rpc.get_token_accounts_by_owner(self.pubkey, opts)

            if response.value:
                # Sum balances from all token accounts
                total = 0.0
                for account in response.value:
                    account_data = account.account.data
                    if hasattr(account_data, "parsed"):
                        amount = account_data.parsed["info"]["tokenAmount"]["uiAmount"]
                        total += float(amount or 0)
                return total
            return 0.0

        except Exception as e:
            LOGGER.error("Failed to get token balance for %s: %s", self.config.name, e)
            return 0.0

    async def get_balance_usd(self, sol_price: float = 0.0) -> float:
        """Get total wallet balance in USD.

        Args:
            sol_price: Current SOL price in USD

        Returns:
            float: Total balance in USD
        """
        sol_balance = await self.get_sol_balance()
        # TODO: Add token balances * prices
        return sol_balance * sol_price


__all__ = ["WalletManager"]
