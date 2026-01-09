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
