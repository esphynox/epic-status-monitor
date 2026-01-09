# Deployment & Configuration

## Adjust Polling Frequency

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

## Deploying to Cloudflare Workers

1. **Install Wrangler CLI**
   
   ```bash
   npm install -g wrangler
   # or
   brew install wrangler
   ```

2. **Authenticate Wrangler**
   
   ```bash
   wrangler login
   ```

3. **Configure `wrangler.toml`**
   
   Copy the example configuration file and customize it:
   
   ```bash
   cd worker
   cp wrangler.example.toml wrangler.toml
   ```
   
   > ⚠️ **Important:** The `wrangler.toml` file contains your secrets (KV namespace IDs). Do not commit this file to git. The `wrangler.example.toml` file is already in the repository as a template.
   
   The example file is pre-configured with the correct name, main entry, and compatibility date. You'll need to update it with your KV namespace IDs in the next step.

4. **Create KV Namespaces**
   
   ```bash
   wrangler kv namespace create STATE
   wrangler kv namespace create SUBSCRIPTIONS
   ```
   
   Copy the namespace IDs from the output and update your `wrangler.toml` file accordingly, replacing the placeholder values (`YOUR_STATE_KV_ID` and `YOUR_SUBS_KV_ID`).

5. **Set Secrets**
   
   ```bash
   wrangler secret put TELEGRAM_TOKEN
   wrangler secret put WEBHOOK_SECRET
   ```
   
   Enter your bot token and webhook secret when prompted.

6. **Publish the Worker**
   
   ```bash
   wrangler deploy
   ```

Your bot should now be running on Cloudflare Workers! Check your Telegram for notifications and monitor the Cloudflare dashboard for logs and status.
