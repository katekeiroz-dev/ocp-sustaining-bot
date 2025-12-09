# Quick Start Guide - Slack Worker Service

##  Get Started in 5 Minutes

### 1. Prerequisites

- Python 3.12+
- Docker (optional, for containerized deployment)
- Slack workspace with bot configured
- Google Sheets with ROTA data
- Smartsheet access (optional, for sync feature)

### 2. Installation

```bash
# Navigate to slack_worker directory
cd slack_worker

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env  # or your preferred editor
```

**Minimum required configuration:**

```bash
# Slack
SLACK_BOT_TOKEN=xoxb-your-token
ROTA_GROUP_CHANNEL=C12345...

# Google Sheets
ROTA_SERVICE_ACCOUNT={"type":"service_account",...}

# User mapping
ROTA_USERS={"john.doe":"U12345","jane.smith":"U67890"}
```

### 4. Run Locally

```bash
# From slack_worker directory
python -m slack_worker.main
```

You should see:

```
2024-01-01 09:00:00 - slack_worker.main - INFO - Starting Slack Worker Service
2024-01-01 09:00:00 - slack_worker.main - INFO - Configuration validation successful
2024-01-01 09:00:00 - slack_worker.scheduler - INFO - Initialized job scheduler
2024-01-01 09:00:00 - slack_worker.main - INFO - Slack Worker Service is running
```

### 5. Verify It's Working

The service will run scheduled jobs automatically. To test immediately, you can:

**Option A: Adjust schedule for testing**

In `.env`, set a job to run every minute:

```bash
SCHEDULE_GROUP_REMINDER=* * * * *  # Every minute
```

**Option B: Run tests**

```bash
pytest tests/ -v
```

##  Docker Quick Start

### Build and Run

```bash
# From project root
docker build -f slack_worker/Dockerfile -t slack-worker:latest .

# Run container
docker run --env-file .env slack-worker:latest
```

### Using Docker Compose

```bash
cd slack_worker
docker-compose up
```


##  Job Schedules

Default schedules (all times in configured timezone):

| Job | Schedule | Description |
|-----|----------|-------------|
| Group Reminder | Mon & Thu @ 9 AM | Post releases to Slack channel |
| DM Reminder | Fri @ 5 PM | Remind assignees (week ending) |
| DM Reminder | Mon @ 9 AM | Remind assignees (week starting) |
| Sheet Sync | Daily @ 8 AM | Sync Smartsheet to Google Sheets |

## 🔧 Common Customizations

### Change Schedule

Edit `.env`:

```bash
# Run group reminders at 10 AM instead
SCHEDULE_GROUP_REMINDER=0 10 * * MON,THU

# Run sheet sync every 6 hours
SCHEDULE_SHEET_SYNC=0 */6 * * *
```

### Disable a Job

```bash
ENABLE_GROUP_REMINDER=false
```

### Change Timezone

```bash
TIMEZONE=America/New_York
```

##  Troubleshooting

### Logs show "Configuration validation failed"

**Problem:** Missing required environment variables

**Solution:** Check that you have set:
- `SLACK_BOT_TOKEN`
- `ROTA_SERVICE_ACCOUNT`
- `ROTA_GROUP_CHANNEL` (if group reminders enabled)

### Jobs are not running

**Problem:** Incorrect cron expression or timezone

**Solution:**
1. Verify cron expression at [crontab.guru](https://crontab.guru/)
2. Check timezone setting matches your desired schedule
3. Look for scheduler errors in logs

### "Permission denied" errors

**Problem:** Insufficient Slack permissions or wrong channel ID

**Solution:**
1. Verify bot is added to the channel
2. Check bot has `chat:write` permission
3. Verify channel ID is correct (starts with 'C')

### Multiple job executions (in scaled deployment)

**Problem:** Locking not working properly

**Solution:**
1. Verify shared PVC is mounted to all pods
2. Check `LOCK_DIR` is writable
3. Ensure pods use the same storage

##  Next Steps

- Read full [README.md](README.md) for detailed documentation
- Review [CONTRIBUTING.md](CONTRIBUTING.md) for development guide
- Explore job implementations in `jobs/` directory

##  Tips

1. **Test in development first**: Use a test Slack workspace and Google Sheet
2. **Start with one job**: Enable only one job initially to test
3. **Monitor logs**: Keep logs visible when first deploying
4. **Use UTC for schedules**: Avoids daylight saving time issues
5. **Document your config**: Keep notes on your specific configuration

##  Getting Help

- Check logs for error messages
- Review configuration in `.env`
- Run tests to verify setup: `pytest tests/ -v`
- Check Slack bot permissions
- Verify Google Sheets access

---

**Ready to deploy?** See [README.md](README.md) for production deployment guide.

