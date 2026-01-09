# Epic Games Status Monitor 🎮

A lightweight bot that monitors [status.epicgames.com](https://status.epicgames.com) for incidents and sends notifications to Telegram.

## Features

- 🔔 **Real-time notifications** for new incidents
- 🔄 **Update tracking** - get notified when incidents are updated
- 📊 **Status tracking** - monitoring, investigating, identified, resolved
- 🎮 **Component info** - see which Epic services are affected
- 🤖 **Fully automated** via GitHub Actions (runs every 10 minutes)
- 💸 **100% free** - uses GitHub Actions free tier

## Quick Setup

### 1. Create a Telegram Bot

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts
3. Copy your **Bot Token** (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Get Your Chat ID

**Option A: Personal notifications**
1. Message your new bot (send any message)
2. Visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
3. Find `"chat":{"id":123456789}` - that number is your Chat ID

**Option B: Group notifications**
1. Add your bot to a group
2. Send a message in the group
3. Visit the getUpdates URL above
4. The chat ID will be negative for groups (e.g., `-1001234567890`)

### 3. Fork & Configure Repository

1. **Fork this repository** to your GitHub account

2. **Add secrets** in your repo settings (`Settings` → `Secrets and variables` → `Actions`):
   
   | Secret Name | Value |
   |-------------|-------|
   | `TELEGRAM_TOKEN` | Your bot token from BotFather |
   | `TELEGRAM_CHAT_ID` | Your chat/group ID |

3. **Enable Actions** - Go to `Actions` tab and enable workflows if prompted

### 4. Test It

1. Go to `Actions` → `Poll Epic Games Status`
2. Click `Run workflow` → `Run workflow`
3. Check your Telegram for any current incidents!

## How It Works

```
┌─────────────────────────────────────────┐
│        GitHub Actions (every 10min)      │
│                                          │
│  1. Fetch status.epicgames.com API       │
│  2. Compare with seen_incidents.json     │
│  3. Send Telegram if new/updated         │
│  4. Commit updated state                 │
└─────────────────────────────────────────┘
```

The bot uses a simple JSON file to track which incidents it has already notified about. This means:
- ✅ No external database needed
- ✅ State persists between runs
- ⚠️ Creates a commit when state changes (usually only during incidents)

## Example Notification

```
🚨 NEW INCIDENT

🔍 Epic Games Store Login Issues
Status: Investigating
Impact: 🟠 Major

📋 We are currently investigating issues with logging into 
the Epic Games Store. Updates will follow.

🎮 Affected: Epic Games Store, Launcher

🔗 https://stspg.io/abc123
```

## Local Development

Test the script locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Run without Telegram (prints to console)
python poll_status.py

# Run with Telegram
export TELEGRAM_TOKEN="your-token"
export TELEGRAM_CHAT_ID="your-chat-id"
python poll_status.py
```

## Configuration

### Adjust Polling Frequency

Edit `.github/workflows/poll.yml`:

```yaml
on:
  schedule:
    - cron: '*/5 * * * *'   # Every 5 minutes
    - cron: '*/10 * * * *'  # Every 10 minutes (default)
    - cron: '*/30 * * * *'  # Every 30 minutes
```

> ⚠️ GitHub Actions has [usage limits](https://docs.github.com/en/actions/learn-github-actions/usage-limits-and-billing). For private repos, you get 2000 minutes/month free.

## Troubleshooting

### Bot not sending messages?
- Verify secrets are set correctly in repo settings
- Check that you've messaged the bot first (required for personal chats)
- Look at the Actions run logs for errors

### Getting duplicate notifications?
- The `seen_incidents.json` might have been reset
- Check if there were merge conflicts

### Want to reset tracking?
Edit `seen_incidents.json` and set `"seen_ids": []`

## License

MIT - do whatever you want with it! 🎉

## Credits

- Status data from [status.epicgames.com](https://status.epicgames.com) (powered by Statuspage.io)
- Built with ❤️ for the Epic Games community
