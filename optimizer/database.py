from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import String, Float, DateTime, Integer, Boolean, ForeignKey, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

LOGGER = logging.getLogger("optimizer.database")


class Base(DeclarativeBase):
    pass


class VaultRecord(Base):
    __tablename__ = "vaults"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    platform: Mapped[str] = mapped_column(String(50))
    pool_address: Mapped[Optional[str]] = mapped_column(String(100))
    token_a: Mapped[Optional[str]] = mapped_column(String(20))
    token_b: Mapped[Optional[str]] = mapped_column(String(20))
    apy: Mapped[float] = mapped_column(Float)
    tvl_usd: Mapped[float] = mapped_column(Float)
    fee_bps: Mapped[int] = mapped_column(Integer)
    volatility_score: Mapped[float] = mapped_column(Float)
    liquidity_score: Mapped[float] = mapped_column(Float)
    url: Mapped[str] = mapped_column(String(200))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class PositionRecord(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    wallet_name: Mapped[str] = mapped_column(String(50), index=True)
    vault_name: Mapped[str] = mapped_column(String(100), index=True)
    vault_platform: Mapped[str] = mapped_column(String(50))
    amount_usd: Mapped[float] = mapped_column(Float)
    deposited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_harvest: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    total_harvested_usd: Mapped[float] = mapped_column(Float, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    harvests: Mapped[List["HarvestRecord"]] = relationship(back_populates="position", cascade="all, delete-orphan")


class HarvestRecord(Base):
    __tablename__ = "harvests"

    id: Mapped[int] = mapped_column(primary_key=True)
    position_id: Mapped[int] = mapped_column(ForeignKey("positions.id"), index=True)
    yield_usd: Mapped[float] = mapped_column(Float)
    harvested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    transaction_signature: Mapped[Optional[str]] = mapped_column(String(100))

    position: Mapped["PositionRecord"] = relationship(back_populates="harvests")


class RebalanceRecord(Base):
    __tablename__ = "rebalances"

    id: Mapped[int] = mapped_column(primary_key=True)
    from_vault: Mapped[Optional[str]] = mapped_column(String(100))
    to_vault: Mapped[str] = mapped_column(String(100))
    amount_usd: Mapped[float] = mapped_column(Float)
    from_apy: Mapped[Optional[float]] = mapped_column(Float)
    to_apy: Mapped[float] = mapped_column(Float)
    wallet_name: Mapped[str] = mapped_column(String(50))
    rebalanced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    transaction_signature: Mapped[Optional[str]] = mapped_column(String(100))


class Database:
    """Database manager for persistence."""

    def __init__(self, database_url: str = "sqlite+aiosqlite:///./optimizer.db") -> None:
        self.engine = create_async_engine(database_url, echo=False)
        self.async_session = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

    async def init_db(self) -> None:
        """Initialize database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        LOGGER.info("Database initialized")

    async def record_vault_snapshot(self, vaults: List) -> None:
        """Record current vault metrics for historical analysis."""
        from optimizer.models import Vault

        async with self.async_session() as session:
            for vault in vaults:
                if not isinstance(vault, Vault):
                    continue

                record = VaultRecord(
                    name=vault.name,
                    platform=vault.platform,
                    pool_address=vault.pool_address,
                    token_a=vault.token_a,
                    token_b=vault.token_b,
                    apy=vault.apy,
                    tvl_usd=vault.tvl_usd,
                    fee_bps=vault.fee_bps,
                    volatility_score=vault.volatility_score,
                    liquidity_score=vault.liquidity_score,
                    url=vault.url,
                )
                session.add(record)

            await session.commit()
            LOGGER.debug("Recorded %d vault snapshots", len(vaults))

    async def get_active_positions(self) -> List[PositionRecord]:
        """Get all active positions."""
        async with self.async_session() as session:
            result = await session.execute(
                select(PositionRecord).where(PositionRecord.is_active == True)
            )
            return list(result.scalars().all())

    async def create_position(self, position) -> PositionRecord:
        """Create a new position record."""
        from optimizer.models import VaultPosition

        if not isinstance(position, VaultPosition):
            raise ValueError("Invalid position object")

        async with self.async_session() as session:
            record = PositionRecord(
                wallet_name=position.wallet,
                vault_name=position.vault.name,
                vault_platform=position.vault.platform,
                amount_usd=position.amount_usd,
                deposited_at=position.deposited_at,
                last_harvest=position.last_harvest,
                total_harvested_usd=position.total_harvested_usd,
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            LOGGER.info("Created position record: %s in %s", record.wallet_name, record.vault_name)
            return record

    async def record_harvest(self, position_id: int, yield_usd: float, signature: Optional[str] = None) -> None:
        """Record a harvest event."""
        async with self.async_session() as session:
            harvest = HarvestRecord(
                position_id=position_id,
                yield_usd=yield_usd,
                transaction_signature=signature,
            )
            session.add(harvest)
            await session.commit()
            LOGGER.info("Recorded harvest: $%.2f for position %d", yield_usd, position_id)

    async def record_rebalance(
        self,
        from_vault: Optional[str],
        to_vault: str,
        amount_usd: float,
        from_apy: Optional[float],
        to_apy: float,
        wallet_name: str,
        signature: Optional[str] = None,
    ) -> None:
        """Record a rebalance event."""
        async with self.async_session() as session:
            rebalance = RebalanceRecord(
                from_vault=from_vault,
                to_vault=to_vault,
                amount_usd=amount_usd,
                from_apy=from_apy,
                to_apy=to_apy,
                wallet_name=wallet_name,
                transaction_signature=signature,
            )
            session.add(rebalance)
            await session.commit()
            LOGGER.info("Recorded rebalance: %s -> %s ($%.2f)", from_vault or "None", to_vault, amount_usd)

    async def close_position(self, position_id: int) -> None:
        """Mark a position as closed."""
        async with self.async_session() as session:
            result = await session.execute(
                select(PositionRecord).where(PositionRecord.id == position_id)
            )
            position = result.scalar_one_or_none()
            if position:
                position.is_active = False
                position.closed_at = datetime.now(timezone.utc)
                await session.commit()
                LOGGER.info("Closed position %d", position_id)


__all__ = ["Database", "VaultRecord", "PositionRecord", "HarvestRecord", "RebalanceRecord"]
