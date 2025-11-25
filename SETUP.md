# Setup Guide

Complete setup instructions for the Solana Yield Farming Optimizer.

## Prerequisites

- Python 3.10 or higher
- Git
- A Solana wallet with funds
- (Optional) Telegram bot token for notifications
- (Optional) Discord webhook for notifications

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/machenxi/solana-yield-farmer.git
cd solana-yield-farmer
```

### 2. Create Virtual Environment

```bash
python -m venv .venv

# On Linux/Mac:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -e .
```

For development:
```bash
pip install -e ".[dev]"
```

## Configuration

### 1. Create Environment File

```bash
cp .env.example .env
```

Edit `.env` and set your values:

```bash
# Use a premium RPC for better performance (recommended)
SOLANA_RPC_URL=https://rpc.helius.xyz/?api-key=YOUR_API_KEY

# Your wallet addresses
WALLET_1_ADDRESS=YourWalletPublicKeyHere
WALLET_1_KEY_PATH=secrets/primary.json

# Telegram (optional)
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789

# Discord (optional)
DISCORD_ENABLED=false
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### 2. Create Configuration File

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml` to customize your strategy:

```yaml
strategy:
  harvest_interval_minutes: 180      # Harvest every 3 hours
  rotation_threshold_bps: 75         # Rotate if APY diff > 0.75%
  min_apy: 6.0                       # Only consider vaults with >6% APY
  slippage_bps: 30                   # 0.3% max slippage
  target_vaults: []                  # Empty = all vaults
```

### 3. Set Up Wallet Keypairs

Create a `secrets/` directory and add your wallet keypairs:

```bash
mkdir -p secrets
```

Export your Solana wallet as JSON (array of 64 bytes):
```json
[123, 45, 67, ... (64 numbers total)]
```

Save it as `secrets/primary.json`.

**⚠️ SECURITY WARNING:**
- Never commit keypair files to git
- Set proper file permissions: `chmod 600 secrets/*.json`
- Consider using hardware wallets for large amounts

## Getting RPC Access

For production use, get a dedicated RPC endpoint:

### Helius (Recommended)
1. Sign up at https://helius.xyz
2. Create an API key
3. Use: `https://rpc.helius.xyz/?api-key=YOUR_KEY`

### Alchemy
1. Sign up at https://alchemy.com
2. Create a Solana app
3. Use: `https://solana-mainnet.g.alchemy.com/v2/YOUR_KEY`

### QuickNode
1. Sign up at https://quicknode.com
2. Create a Solana endpoint
3. Use the provided URL

## Telegram Bot Setup (Optional)

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow instructions
3. Copy the bot token
4. Add bot to a channel/group and send a message
5. Get chat ID by visiting: `https://api.telegram.org/bot<TOKEN>/getUpdates`
6. Look for `"chat":{"id":123456789}`

## Discord Webhook Setup (Optional)

1. Open Discord server settings
2. Go to Integrations → Webhooks
3. Click "New Webhook"
4. Copy the webhook URL
5. Paste into `.env` as `DISCORD_WEBHOOK_URL`

## Database Setup

By default, uses SQLite (no setup needed). For PostgreSQL:

1. Install PostgreSQL
2. Create database: `createdb optimizer`
3. Update `.env`:
   ```
   DATABASE_URL=postgresql+asyncpg://user:password@localhost/optimizer
   ```

## Running the Optimizer

### Test Configuration

Verify everything works:
```bash
solana-optimizer once -c config.yaml
```

This runs a single cycle and shows the dashboard.

### Continuous Monitoring

Run continuously with auto-refresh:
```bash
solana-optimizer serve -c config.yaml
```

Press `Ctrl+C` to stop.

### Manual Harvest

Force a harvest cycle:
```bash
solana-optimizer harvest -c config.yaml
```

## Monitoring

### View Logs

```bash
# Set logging level
export LOG_LEVEL=DEBUG
solana-optimizer serve -c config.yaml
```

### Database Queries

```bash
sqlite3 optimizer.db
```

Example queries:
```sql
-- View all positions
SELECT * FROM positions WHERE is_active = 1;

-- View harvest history
SELECT * FROM harvests ORDER BY harvested_at DESC LIMIT 10;

-- View rebalance history
SELECT * FROM rebalances ORDER BY rebalanced_at DESC LIMIT 10;

-- Calculate total earnings
SELECT SUM(yield_usd) FROM harvests;
```

## Production Deployment

### Using systemd (Linux)

Create `/etc/systemd/system/solana-optimizer.service`:

```ini
[Unit]
Description=Solana Yield Farming Optimizer
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/solana-yield-farmer
Environment="PATH=/path/to/solana-yield-farmer/.venv/bin"
ExecStart=/path/to/.venv/bin/solana-optimizer serve -c config.yaml
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable solana-optimizer
sudo systemctl start solana-optimizer
sudo systemctl status solana-optimizer
```

View logs:
```bash
sudo journalctl -u solana-optimizer -f
```

### Using Docker (TODO)

Coming soon!

### Using PM2 (Alternative)

```bash
npm install -g pm2
pm2 start "solana-optimizer serve -c config.yaml" --name solana-optimizer
pm2 save
pm2 startup
```

## Troubleshooting

### RPC Connection Errors

**Error:** `Connection refused` or `Timeout`

**Solution:**
- Check your RPC URL in `.env`
- Verify your RPC provider is online
- Try using a different RPC provider
- Check firewall/network settings

### Provider API Failures

**Error:** `Failed to fetch Raydium/Meteora/Orca pools`

**Solution:**
- Providers will fallback to cached or mock data
- Check provider API status
- Wait and retry (APIs may be temporarily down)
- Check logs for specific error messages

### Wallet Loading Errors

**Error:** `Keypair file not found` or `Invalid keypair format`

**Solution:**
- Verify file path in config.yaml
- Check file exists: `ls -la secrets/`
- Verify JSON format (array of 64 numbers)
- Check file permissions

### Database Errors

**Error:** `Database locked` or `Unable to open database`

**Solution:**
- Only run one instance at a time
- Check file permissions on `optimizer.db`
- For PostgreSQL, verify connection string
- Try deleting `optimizer.db` to start fresh (loses history)

### Import Errors

**Error:** `ModuleNotFoundError: No module named 'solana'`

**Solution:**
- Activate virtual environment: `source .venv/bin/activate`
- Reinstall: `pip install -e .`
- Check Python version: `python --version` (must be 3.10+)

## Security Best Practices

1. **Never commit secrets to git**
   - Use `.gitignore` (already configured)
   - Use environment variables for sensitive data

2. **Protect wallet keypairs**
   - Store in `secrets/` directory
   - Set file permissions: `chmod 600 secrets/*.json`
   - Consider hardware wallets for production

3. **Use secure RPC endpoints**
   - Don't use public RPCs for production
   - Use rate-limited, authenticated endpoints

4. **Monitor regularly**
   - Check logs daily
   - Set up alerts for failures
   - Monitor wallet balances

5. **Test with small amounts first**
   - Start with minimal capital
   - Verify rotations work correctly
   - Scale up gradually

## Getting Help

- **Issues:** https://github.com/machenxi/solana-yield-farmer/issues
- **Discussions:** https://github.com/machenxi/solana-yield-farmer/discussions
- **Email:** xsui46941@gmail.com
- **Telegram:** @lorine93s
- **Twitter:** @kakamajo_btc

## Next Steps

Once set up:
1. Run `solana-optimizer once` to verify configuration
2. Monitor for 24 hours to see vault data updates
3. Review rebalance logic and thresholds
4. Enable production mode with `serve` command
5. Set up monitoring and alerts
6. Scale capital allocation gradually

Happy yield farming! 🌾
