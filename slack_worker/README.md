# Slack Worker Service

A scheduled job service for automating Slack notifications and data synchronization tasks related to the OCP ROTA (Release Rotation) management.

## Features

### 1. **ROTA Group Reminders**
- Posts release information to a Slack channel every Monday and Thursday
- Monday: Shows current week and next week releases
- Thursday: Mid-week reminder with current week releases

### 2. **ROTA DM Reminders**
- Sends direct messages to individuals involved in releases
- Friday (5 PM): Reminder about current week releases (wrapping up)
- Monday (9 AM): Reminder about current week releases (starting)

### 3. **Smartsheet to Google Sheets Sync**
- Automatically syncs release data from Smartsheet to Google Sheets
- Runs daily at 8 AM (configurable)
- Maintains sync history for reference

### 4. **Horizontal Scaling Support**
- File-based locking mechanism prevents duplicate job execution
- Safe for multi-pod deployments in Kubernetes/OpenShift
- Uses shared PVC for coordination

## Architecture

```
slack_worker/
├── __init__.py              # Package initialization
├── main.py                  # Main entry point
├── config.py                # Configuration management
├── scheduler.py             # APScheduler with file locking
├── slack_client.py          # Slack API wrapper
├── jobs/                    # Job implementations
│   ├── __init__.py
│   ├── rota_reminders.py   # ROTA reminder jobs
│   └── sheet_sync.py       # Smartsheet sync job
├── smartsheet_client/       # Smartsheet integration
│   ├── __init__.py
│   └── smartsheet_reader.py
├── tests/                   # Unit tests
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_scheduler.py
│   ├── test_rota_reminders.py
│   ├── test_sheet_sync.py
│   └── test_slack_client.py
├── Dockerfile               # Container build file
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Configuration

### Required Environment Variables

```bash
# Slack Configuration (inherited from main bot)
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...

# Google Sheets Configuration
ROTA_SERVICE_ACCOUNT={"type":"service_account",...}
ROTA_SHEET=ROTA
ROTA_SYNC_WORKSHEET=Smartsheet_Sync
ASSIGNMENT_WSHEET=Assignments

# Smartsheet Configuration
SMARTSHEET_ACCESS_TOKEN=your_smartsheet_token
SMARTSHEET_SHEET_ID=your_sheet_id
SMARTSHEET_SOURCE_URL=https://app.smartsheet.com/b/publish?EQBCT=...

# Slack Channel/User Configuration
ROTA_GROUP_CHANNEL=C12345...  # Channel ID for group notifications
ROTA_USERS={"user.name":"U12345",...}  # User mapping

# Team Configuration
ROTA_LEADS=lead1,lead2,lead3
ROTA_MEMBERS=member1,member2,member3
```

### Optional Environment Variables

```bash
# Job Scheduling (cron expressions)
SCHEDULE_GROUP_REMINDER="0 9 * * MON,THU"      # Mon/Thu at 9 AM
SCHEDULE_DM_REMINDER_FRIDAY="0 17 * * FRI"     # Fri at 5 PM
SCHEDULE_DM_REMINDER_MONDAY="0 9 * * MON"      # Mon at 9 AM
SCHEDULE_SHEET_SYNC="0 8 * * *"                # Daily at 8 AM

# Enable/Disable Jobs
ENABLE_GROUP_REMINDER=true
ENABLE_DM_REMINDER=true
ENABLE_SHEET_SYNC=true

# File Locking (for horizontal scaling)
LOCK_DIR=/tmp/slack_worker_locks
LOCK_TIMEOUT=300  # seconds

# Other
TIMEZONE=UTC
LOG_LEVEL=INFO
```

## Running Locally

### Prerequisites

- Python 3.12+
- Virtual environment
- Access to Slack workspace and Google Sheets

### Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
cd slack_worker
pip install -r requirements.txt

# Set environment variables (create .env file in project root)
cp .env.example .env
# Edit .env with your credentials

# Run the service
python -m slack_worker.main
```

## Running with Docker

### Build Image

```bash
# From project root
docker build -f slack_worker/Dockerfile -t slack-worker:latest .
```

### Run Container

```bash
docker run -d \
  --name slack-worker \
  --env-file .env \
  -v /path/to/locks:/tmp/slack_worker_locks \
  slack-worker:latest
```


## Testing

### Run All Tests

```bash
cd slack_worker
pytest tests/ -v
```

### Run with Coverage

```bash
pytest tests/ --cov=slack_worker --cov-report=html
```

### Run Specific Test File

```bash
pytest tests/test_rota_reminders.py -v
```

## Adding New Jobs

To add a new scheduled job:

1. **Create job function** in `jobs/` directory:

```python
# jobs/my_new_job.py
import logging

logger = logging.getLogger(__name__)

def my_new_job():
    """Description of what this job does"""
    logger.info("Running my new job")
    # Job implementation
    pass
```

2. **Add job to scheduler** in `main.py`:

```python
from slack_worker.jobs import my_new_job

def setup_jobs(scheduler):
    # ... existing jobs ...
    
    scheduler.add_cron_job(
        func=my_new_job,
        job_id='my_new_job',
        cron_expression='0 10 * * *',  # Daily at 10 AM
        use_lock=True
    )
```

3. **Add configuration** in `config.py`:

```python
SCHEDULE_MY_NEW_JOB = os.getenv('SCHEDULE_MY_NEW_JOB', '0 10 * * *')
ENABLE_MY_NEW_JOB = os.getenv('ENABLE_MY_NEW_JOB', 'true').lower() == 'true'
```

4. **Write tests** in `tests/test_my_new_job.py`

## Cron Expression Format

The service uses standard cron syntax:

```
* * * * *
│ │ │ │ │
│ │ │ │ └─── Day of week (0-7, 0 and 7 = Sunday)
│ │ │ └───── Month (1-12)
│ │ └─────── Day of month (1-31)
│ └───────── Hour (0-23)
└─────────── Minute (0-59)
```

Examples:
- `0 9 * * MON,THU` - 9 AM every Monday and Thursday
- `0 17 * * FRI` - 5 PM every Friday
- `0 8 * * *` - 8 AM every day
- `*/30 * * * *` - Every 30 minutes

## File Locking Mechanism

The service uses file-based advisory locking (`fcntl.flock`) to prevent duplicate job execution in horizontally scaled environments:

- Each job gets its own lock file in `LOCK_DIR`
- Locks are automatically released after job completion
- If a lock can't be acquired within `LOCK_TIMEOUT`, the job is skipped
- Safe for use across multiple pods with shared PVC


## Troubleshooting

### Jobs Not Running

1. Check scheduler logs for errors
2. Verify cron expressions are correct
3. Check that jobs are enabled in configuration
4. Verify timezone settings

### Duplicate Job Execution

1. Ensure `use_lock=True` for jobs
2. Verify shared PVC is mounted correctly
3. Check `LOCK_DIR` is writable
4. Verify pods have access to same storage

### Slack Messages Not Sending

1. Verify `SLACK_BOT_TOKEN` is valid
2. Check bot has permission to post in channel
3. Verify `ROTA_GROUP_CHANNEL` ID is correct
4. Check user IDs in `ROTA_USERS` mapping

### Smartsheet Sync Failing

1. Verify `SMARTSHEET_ACCESS_TOKEN` is valid
2. Check `SMARTSHEET_SHEET_ID` is correct
3. Ensure sheet has required columns
4. Verify Google Sheets credentials are valid

## API Wrapper (Future Enhancement)

Similar to the main bot, an API wrapper can be added to expose job management endpoints:

- `POST /jobs/trigger/{job_id}` - Manually trigger a job
- `GET /jobs` - List all scheduled jobs
- `GET /jobs/{job_id}/status` - Get job status
- `GET /jobs/{job_id}/history` - Get job execution history

This would be implemented as a separate FastAPI app running alongside the scheduler.

## Contributing

1. Write tests for new features
2. Follow existing code style
3. Update documentation
4. Test locally before deploying

## License

Internal Red Hat tool - see project root for license information.

