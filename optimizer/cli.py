from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import typer
from rich.console import Console

from optimizer.config import AppConfig
from optimizer.engine import OptimizerEngine

app = typer.Typer(help="Solana Yield Farming Optimizer CLI")
console = Console()


def _load_engine(config_path: Path) -> OptimizerEngine:
    config = AppConfig.load(config_path)
    return OptimizerEngine(config)


@app.command()
def once(config: Path = typer.Option(Path("config.example.yaml"), "--config", "-c")) -> None:
    """Run a single monitoring + rebalance pass."""
    engine = _load_engine(config)
    asyncio.run(engine.run_once())


@app.command()
def serve(config: Path = typer.Option(Path("config.example.yaml"), "--config", "-c")) -> None:
    """Continuously monitor vaults and rotate capital."""
    engine = _load_engine(config)
    asyncio.run(engine.serve())


@app.command()
def harvest(config: Path = typer.Option(Path("config.example.yaml"), "--config", "-c")) -> None:
    """Force a harvest cycle across tracked positions."""
    engine = _load_engine(config)
    asyncio.run(engine.maybe_harvest())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app()

