# Installation & Setup

## 1. Create a Telegram Bot

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts
3. Copy your **Bot Token** (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

## 2. Get Your Chat ID

**Option A: Personal notifications**
1. Message your new bot (send any message)
2. Visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
3. Find `"chat":{"id":123456789}` - that number is your Chat ID

**Option B: Group notifications**
1. Add your bot to a group
2. Send a message in the group
3. Visit the getUpdates URL above
4. The chat ID will be negative for groups (e.g., `-1001234567890`)

## 3. Fork & Configure Repository

1. **Fork this repository** to your GitHub account

2. **Add secrets** in your repo settings (`Settings` → `Secrets and variables` → `Actions`):
   
   | Secret Name | Value |
   |-------------|-------|
   | `TELEGRAM_TOKEN` | Your bot token from BotFather |
   | `TELEGRAM_CHAT_ID` | Your chat/group ID |

3. **Enable Actions** - Go to `Actions` tab and enable workflows if prompted

## 4. Test It

1. Go to `Actions` → `Poll Epic Games Status`
2. Click `Run workflow` → `Run workflow`
3. Check your Telegram for any current incidents!
