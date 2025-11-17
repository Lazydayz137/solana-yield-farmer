# Solana Yield Farming Optimizer

> Automated capital rotation + harvesting engine for Meteora, Raydium, and Orca LP vaults. Built for desks that want deterministic control, transparent logic, and instant visibility into Solana-native yield opportunities.

[![Run CLI](https://img.shields.io/badge/CLI-sola_optim-blue?logo=gnometerminal&logoColor=white)](#quickstart) [![Config Docs](https://img.shields.io/badge/Docs-config.yaml-success?logo=readthedocs&logoColor=white)](#configuration)

## Why This Project Exists

Traditional “auto-compounders” hide execution, lack alerting, and often lag behind when APYs move. This repository provides:

- **Open, auditable logic** written in Python 3.10+
- **gRPC-free, local execution** so keys never leave your machine
- **Provider plug-ins** for each Solana DEX aggregator
- **Deterministic capital rotation rules** you can extend or swap
- **Real-time CLI dashboard** with blended APY, TVL, and wallet allocation

## Architecture Overview

| Layer | Responsibility |
| --- | --- |
| `optimizer.providers.*` | Adapter per venue (Raydium, Meteora, Orca) returning normalized `Vault` objects |
| `optimizer.engine.OptimizerEngine` | Coordinates vault sync, harvest cadence, rotation logic, and notifications |
| `optimizer.analytics.dashboard` | Renders Rich-powered terminal dashboard |
| `optimizer.notifiers.*` | Telegram + Discord transports with graceful opt-in |
| `optimizer.cli` | Typer CLI to run single pass, daemon, or forced harvest |

## Feature Highlights

- 🔄 **Dynamic vault rotation** – choose highest APY that meets liquidity/volatility guardrails.
- 🌾 **Scheduled harvesting** – configurable interval with consolidated reporting.
- 📊 **Terminal dashboard** – see platform mix, per-vault stats, and blended APY in real time.
- 📣 **Alerting hooks** – Telegram/Discord messages whenever funds rotate or harvest completes.
- 🧩 **Modular providers** – add new protocols by subclassing `VaultProvider`.
- 🔐 **Local-only secrets** – YAML references key files; nothing ever touches a remote API.

## Quickstart

```bash
python -m venv .venv
.venv\Scripts\activate          # or source .venv/bin/activate
pip install -e .                # installs CLI entrypoint `solana-optimizer`
cp config.example.yaml config.yaml
solana-optimizer once -c config.yaml   # single monitoring cycle
solana-optimizer serve -c config.yaml  # continuous loop with dashboard + alerts
```

## Configuration

Key sections inside `config.yaml`:

| Section | Fields | Notes |
| --- | --- | --- |
| `network` | `rpc_endpoint`, `commitment` | Point to your preferred RPC; commitment defaults to `confirmed`. |
| `wallets[]` | `name`, `address`, `private_key_path`, `max_allocation_pct` | Allocation obeys soft limits to prevent over-exposure per wallet. |
| `strategy` | `harvest_interval_minutes`, `rotation_threshold_bps`, `min_apy`, `slippage_bps`, `target_vaults[]` | Controls cadence plus gating rules for new vault entries. |
| `notifications` | Telegram & Discord tokens/webhooks | Leave `enabled: false` to disable a channel. |
| `analytics` | `dashboard_refresh_seconds` | Trade-off between responsiveness and RPC/API load. |

## CLI Commands

| Command | Description |
| --- | --- |
| `solana-optimizer once` | Fetch APYs, harvest if due, rebalance, and print dashboard one time. |
| `solana-optimizer serve` | Long-running daemon that repeats `once` on the refresh interval. |
| `solana-optimizer harvest` | Immediately run the harvest routine without rotation. |

## Strategy Logic

1. **Vault Sync** – Each provider fetches normalized metrics (`Vault` dataclass).  
2. **Harvest Check** – If `harvest_interval_minutes` elapsed, compute accrued yield per position and send alerts.  
3. **Rotation Decision** – Filter vaults by `target_vaults` + `min_apy`; choose best APY above `rotation_threshold_bps` delta; allocate capital respecting wallet caps.  
4. **Reporting** – Update CLI dashboard and emit Telegram/Discord notices.  

You can modify `OptimizerEngine.rebalance` for more advanced heuristics (risk scoring, volatility weighting, multi-wallet splitting, etc.).

## Extending the System

1. **New Venue** – create `optimizer/providers/<name>.py`, subclass `VaultProvider`, and return `Vault` objects.  
2. **Execution Integration** – replace mocked rotation with actual Solana transactions via Anchor, Helius, or direct RPC.  
3. **Metrics** – plug Prometheus/OpenTelemetry inside `OptimizerEngine.run_once`.  
4. **UI** – feed `DashboardSnapshot` into a web socket or Grafana dashboard.  

## Roadmap Ideas

- ✅ Mock providers & alerts (current release)  
- 🔜 Real transaction signer integration  
- 🔜 Historical performance database + export  
- 🔜 WASM-friendly core for browser dashboards  

## FAQ

**Does this custody my keys?**  
No. Wallet paths point to files on your machine; signing/execution layers are intentionally stubbed so you can integrate your own custody.  

**Can I run it headless on a VPS?**  
Yes. The dashboard uses ANSI output; disable Rich colors by exporting `TERM=dumb` if needed.  

**How often should I harvest?**  
Default is every 3 hours (180 min). Shorter intervals improve compounding but increase RPC + fee overhead.  

---
Licensed under MIT. Contributions, bug reports, and new venue adapters are welcome! Complimentary topics: Solana yield farming, Meteora optimizer, Raydium compounding CLI, Orca LP manager, Solana APY dashboard, DeFi rotation bot.
