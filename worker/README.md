# Epic Games Status Bot - Cloudflare Worker

A Telegram bot that monitors Epic Games status and sends notifications with per-user subscription filters.

## Features

- 🔔 Real-time notifications for incidents and maintenance
- 👤 Per-user subscription preferences
- 🎮 Filter by service (Fortnite, Rocket League, etc.)
- ⚡ Filter by impact level (minor, major, critical)
- 📅 Scheduled maintenance alerts
- 💬 Interactive Telegram commands
- 💸 100% free on Cloudflare Workers

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Subscribe to updates |
| `/unsubscribe` | Stop receiving updates |
| `/settings` | View your subscription |
| `/status` | Check current Epic status |
| `/filter <option>` | Customize notifications |
| `/help` | Show help message |

### Filter Examples

```
/filter fortnite          → Only Fortnite updates
/filter rocket league     → Add Rocket League
/filter incidents         → No maintenance alerts
/filter impact major      → Only major+ incidents
/filter all               → Reset to all services
```

## Setup

### Prerequisites

1. [Cloudflare account](https://dash.cloudflare.com/sign-up) (free)
2. [Node.js](https://nodejs.org/) 18+
3. Telegram bot token from [@BotFather](https://t.me/BotFather)

### Step 1: Install Wrangler CLI

```bash
npm install -g wrangler
wrangler login
```

### Step 2: Create KV Namespaces

```bash
cd worker

# Create KV namespaces
wrangler kv:namespace create STATE
wrangler kv:namespace create SUBSCRIPTIONS
```

Copy the output IDs and update `wrangler.toml`:

```toml
[[kv_namespaces]]
binding = "STATE"
id = "paste-state-id-here"

[[kv_namespaces]]
binding = "SUBSCRIPTIONS"
id = "paste-subscriptions-id-here"
```

### Step 3: Set Secrets

```bash
# Your bot token from @BotFather
wrangler secret put TELEGRAM_TOKEN
# Enter: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz

# Optional: webhook verification secret
wrangler secret put WEBHOOK_SECRET
# Enter: any-random-string
```

### Step 4: Deploy

```bash
npm install
wrangler deploy
```

You'll get a URL like: `https://epic-status-bot.your-account.workers.dev`

### Step 5: Register Webhook

Visit your worker URL with `/setup`:

```
https://epic-status-bot.your-account.workers.dev/setup
```

This registers the webhook with Telegram. You should see: `✅ Webhook registered`

### Step 6: Test It!

Message your bot on Telegram with `/start` 🎉

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Cloudflare Worker                             │
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │   Webhook   │    │    Cron     │    │     KV Storage      │  │
│  │  /webhook   │    │  */10 min   │    │                     │  │
│  │             │    │             │    │  STATE: seen events │  │
│  │  Commands   │    │  Poll Epic  │    │  SUBSCRIPTIONS:     │  │
│  │  from users │    │  & notify   │    │    user preferences │  │
│  └──────┬──────┘    └──────┬──────┘    └─────────────────────┘  │
│         │                  │                                     │
│         └────────┬─────────┘                                     │
│                  ▼                                               │
│         ┌───────────────┐                                        │
│         │ Telegram API  │                                        │
│         │ Send messages │                                        │
│         └───────────────┘                                        │
└─────────────────────────────────────────────────────────────────┘
```

## Local Development

```bash
cd worker
npm install
wrangler dev
```

This starts a local server. Use a tool like [ngrok](https://ngrok.com/) to expose it for webhook testing.

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/webhook` | POST | Telegram webhook (automatic) |
| `/setup` | GET | Register webhook with Telegram |
| `/health` | GET | Health check |
| `/poll` | POST | Manual trigger for testing |

## Customization

### Change Polling Frequency

Edit `wrangler.toml`:

```toml
[triggers]
crons = ["*/5 * * * *"]   # Every 5 minutes
```

### Add More Services

Edit `src/epic-status.ts`:

```typescript
export const KNOWN_SERVICES = [
  'Fortnite',
  'Rocket League',
  // Add more...
];
```

## Troubleshooting

### Bot not responding?

1. Check webhook is registered: visit `/setup`
2. Check logs: `wrangler tail`
3. Verify token: `wrangler secret list`

### Not receiving notifications?

1. Check subscription: `/settings`
2. Check Epic status: `/status`
3. Try `/filter all` to reset filters

### KV errors?

Ensure namespace IDs in `wrangler.toml` match the ones from `wrangler kv:namespace create`

## Cost

**$0** - Cloudflare Workers free tier includes:
- 100,000 requests/day
- 100,000 KV reads/day
- 1,000 KV writes/day
- 5 cron triggers

A typical bot uses <1% of these limits.

## License

MIT
