# Usage Instructions

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

## Telegram Filtering Notifications

You can customize what notifications you receive from the Telegram bot using the /filter command. The new syntax allows for more granular control:

### By Service (multiple allowed)
- `/filter service fortnite, rocket league`
- `/filter service all` (reset to all services)

### By Event Type (multiple allowed)
- `/filter event incidents, maintenance`
- `/filter event incidents` (only incidents)
- `/filter event maintenance` (only maintenance)
- `/filter event` (all event types)

### By Impact (incidents only)
- `/filter impact minor`
- `/filter impact major`
- `/filter impact critical`

### Examples
- `/filter service fortnite, epic games store`
- `/filter event incidents, maintenance`
- `/filter impact major`

You can combine these filters to receive only the notifications you care about from the Telegram bot.
