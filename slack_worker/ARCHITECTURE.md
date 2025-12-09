# Slack Worker Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Slack Worker Service                          │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                     Main Process (main.py)                     │ │
│  │  - Configuration Loading & Validation                          │ │
│  │  - Job Registration                                            │ │
│  │  - Scheduler Initialization                                    │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │              APScheduler (scheduler.py)                        │ │
│  │                                                                │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │ │
│  │  │ Cron Trigger │  │ Cron Trigger │  │ Cron Trigger │        │ │
│  │  │   Mon/Thu    │  │   Fri/Mon    │  │    Daily     │        │ │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘        │ │
│  │         │                 │                 │                 │ │
│  │         ▼                 ▼                 ▼                 │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │ │
│  │  │Group Reminder│  │ DM Reminders │  │ Sheet Sync   │        │ │
│  │  │     Job      │  │     Job      │  │     Job      │        │ │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘        │ │
│  └─────────┼──────────────────┼──────────────────┼───────────────┘ │
│            │                  │                  │                  │
│  ┌─────────▼──────────────────▼──────────────────▼───────────────┐ │
│  │              File Lock Manager (scheduler.py)                 │ │
│  │  - Acquires lock before job execution                         │ │
│  │  - Releases lock after completion                             │ │
│  │  - Prevents duplicate execution across pods                   │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
        ┌──────────────────────┐    ┌──────────────────────┐
        │   Shared PVC         │    │   External Services  │
        │   (Lock Files)       │    │                      │
        │  /tmp/locks/         │    │  - Slack API         │
        │  ├─ group_job.lock   │    │  - Google Sheets API │
        │  ├─ dm_job.lock      │    │  - Smartsheet API    │
        │  └─ sync_job.lock    │    │                      │
        └──────────────────────┘    └──────────────────────┘
```

## Component Architecture

### 1. Main Application (`main.py`)

**Responsibilities:**
- Load and validate configuration
- Initialize APScheduler
- Register all jobs with their schedules
- Start blocking scheduler
- Handle graceful shutdown

**Flow:**
```
Start → Validate Config → Create Scheduler → Register Jobs → Start Scheduler → Run
```

### 2. Scheduler (`scheduler.py`)

**Components:**

#### JobScheduler Class
- Wraps APScheduler BlockingScheduler
- Manages job lifecycle
- Provides cron and interval job APIs
- Event listeners for monitoring

#### FileLock Class
- Implements file-based locking using `fcntl.flock`
- Ensures single execution across multiple pods
- Configurable timeout
- Automatic lock release

#### with_lock Decorator
- Wraps job functions with locking logic
- Skips execution if lock unavailable
- Logs lock acquisition/release

**Lock Mechanism Flow:**
```
Job Triggered
    │
    ▼
Try Acquire Lock ──No──▶ Wait (with timeout)
    │                         │
   Yes                        │
    │                    Timeout? ──Yes──▶ Skip Job (log warning)
    │                         │
    ▼                        No
Execute Job                   │
    │                         │
    ▼                         │
Release Lock ◀────────────────┘
```

### 3. Jobs Module (`jobs/`)

#### rota_reminders.py

**Functions:**
- `get_current_week_releases()` - Fetch current week data
- `get_next_week_releases()` - Fetch next week data
- `format_release_message()` - Format for Slack
- `send_group_reminder()` - Post to channel
- `send_dm_reminders()` - Send DMs to assignees

**Data Flow:**
```
Google Sheets → Fetch Releases → Format Messages → Slack API → Users
```

#### sheet_sync.py

**Classes:**
- `SheetSyncManager` - Manages Google Sheets operations

**Functions:**
- `sync_smartsheet_to_gsheet()` - Main sync job
- `get_week_range()` - Date calculations

**Data Flow:**
```
Smartsheet API → Parse Releases → Add Metadata → Google Sheets API → Sync Worksheet
```

### 4. Slack Client (`slack_client.py`)

**SlackClient Class:**
- `send_message()` - Send to channel
- `send_dm()` - Send direct message
- `get_user_info()` - Fetch user details

**Features:**
- Error handling for API errors
- Automatic channel opening for DMs
- Logging of all operations

### 5. Smartsheet Client (`smartsheet_client/`)

**Functions:**
- `get_smartsheet_releases()` - Fetch and filter releases
- `get_week_range()` - Date utilities

**Features:**
- Handles multiple date formats
- Filters for current + next week
- Column name flexibility

### 6. Configuration (`config.py`)

**WorkerConfig Class:**
- Inherits from main bot config
- Loads environment variables
- Provides defaults
- Validation logic

**Configuration Sources:**
```
Environment Variables → .env file → Vault (optional) → Defaults
```

## Deployment Architectures

### Single Pod Deployment

```
┌─────────────────────────────────┐
│       Kubernetes Pod            │
│                                 │
│  ┌───────────────────────────┐  │
│  │   Slack Worker Container  │  │
│  │   - Scheduler             │  │
│  │   - All Jobs              │  │
│  │   - Lock Dir: /tmp/locks  │  │
│  └───────────────────────────┘  │
│                                 │
│  Volume: /tmp/locks (emptyDir)  │
└─────────────────────────────────┘
```

**Notes:**
- No locking overhead (single instance)
- Simpler deployment
- No high availability

### Horizontal Scaled Deployment

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   Pod 1             │    │   Pod 2             │    │   Pod 3             │
│  ┌───────────────┐  │    │  ┌───────────────┐  │    │  ┌───────────────┐  │
│  │Slack Worker   │  │    │  │Slack Worker   │  │    │  │Slack Worker   │  │
│  │- All Jobs     │  │    │  │- All Jobs     │  │    │  │- All Jobs     │  │
│  └───────────────┘  │    │  └───────────────┘  │    │  └───────────────┘  │
└──────────┬──────────┘    └──────────┬──────────┘    └──────────┬──────────┘
           │                          │                          │
           └──────────────────────────┼──────────────────────────┘
                                      │
                           ┌──────────▼──────────┐
                           │   Shared PVC        │
                           │   (ReadWriteMany)   │
                           │   /tmp/locks/       │
                           │   - Job lock files  │
                           └─────────────────────┘
```

**Benefits:**
- High availability (pod failure tolerant)
- Load distribution
- Auto-scaling capability

**Requirements:**
- ReadWriteMany PVC
- File locking enabled

## Job Execution Flow

### Group Reminder Job (Monday/Thursday)

```
┌─────────────────┐
│ Cron Trigger    │ (Mon/Thu 9:00 AM)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Acquire Lock    │ (job_rota_group_reminder)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Fetch Releases  │ (Google Sheets API)
│ - This Week     │
│ - Next Week     │ (Monday only)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Format Message  │
│ - Release info  │
│ - User mentions │
│ - Dates         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Send to Channel │ (Slack API)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Release Lock    │
└─────────────────┘
```

### DM Reminder Job (Friday/Monday)

```
┌─────────────────┐
│ Cron Trigger    │ (Fri 5PM / Mon 9AM)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Acquire Lock    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Fetch Releases  │ (This Week)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Extract Users   │
│ - PM            │
│ - QE1, QE2      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ For Each User   │─────┐
└────────┬────────┘     │
         │              │
         │   ┌──────────▼─────────┐
         │   │ Open DM Channel    │
         │   └──────────┬─────────┘
         │              │
         │   ┌──────────▼─────────┐
         │   │ Format Message     │
         │   │ - Role (PM/QE)     │
         │   │ - Release details  │
         │   └──────────┬─────────┘
         │              │
         │   ┌──────────▼─────────┐
         │   │ Send DM            │
         │   └──────────┬─────────┘
         │              │
         └◀─────────────┘
         │
         ▼
┌─────────────────┐
│ Release Lock    │
└─────────────────┘
```

### Sheet Sync Job (Daily)

```
┌─────────────────┐
│ Cron Trigger    │ (Daily 8:00 AM)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Acquire Lock    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Fetch from      │
│ Smartsheet      │ (Current + Next Week)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Add Metadata    │
│ - Leads         │ (from env vars)
│ - Members       │ (from env vars)
│ - Timestamp     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Update GSheet   │
│ (Sync Worksheet)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Release Lock    │
└─────────────────┘
```

## Error Handling Strategy

### Job-Level Error Handling

```python
def job_function():
    try:
        # Job logic
        pass
    except SpecificException as e:
        logger.error(f"Specific error: {e}")
        # Handle specific case
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise  # Re-raise for scheduler to log
```

### Lock Timeout Handling

```python
try:
    with FileLock("job_name"):
        execute_job()
except TimeoutError:
    logger.warning("Job skipped - another instance running")
    # Don't raise - this is expected in scaled environments
```

### External API Error Handling

```python
try:
    response = slack_client.send_message(...)
    if not response:
        logger.error("Failed to send message")
        # Continue with other operations
except SlackApiError as e:
    logger.error(f"Slack API error: {e}")
    # Don't crash entire job
```

## Security Considerations

### Secrets Management

```
Secrets (Vault/K8s Secret)
    │
    ├─ SLACK_BOT_TOKEN → Environment → Config
    ├─ ROTA_SERVICE_ACCOUNT → Environment → Config
    └─ SMARTSHEET_ACCESS_TOKEN → Environment → Config
```

### Access Control

- Bot token has minimal required scopes
- Service account has read-only access where possible
- Smartsheet token can be read-only (if not modifying)

### Data Protection

- No sensitive data logged
- Lock files contain only PID and timestamp
- Temporary files cleaned up

## Monitoring & Observability

### Logging Levels

```
DEBUG:   Lock operations, detailed job steps
INFO:    Job start/complete, configuration loaded
WARNING: Lock timeout, skipped execution
ERROR:   Job failures, API errors
```

### Key Metrics to Monitor

1. **Job Execution:**
   - Success/failure rate
   - Execution duration
   - Lock contention frequency

2. **External APIs:**
   - Slack API response times
   - Google Sheets API rate limits
   - Smartsheet API availability

3. **System Resources:**
   - CPU usage
   - Memory usage
   - Lock file count/size

### Health Checks

```
Liveness:  Lock directory exists and writable
Readiness: Scheduler initialized and jobs registered
```

## Scalability Considerations

### Horizontal Scaling

**Supports:** 2-10 pods (typical)
**Limit:** PVC I/O capacity for lock files

**Scaling Triggers:**
- Resource utilization (CPU/Memory)
- Job execution frequency
- Required availability level

### Performance Optimization

1. **Lock Timeout:** Tune based on job duration
2. **Job Isolation:** Each job has independent lock
3. **Efficient Queries:** Minimize API calls

## Future Extensibility

### Adding New Job Types

```python
# 1. Create job function
def new_job():
    pass

# 2. Register in scheduler
scheduler.add_cron_job(
    func=new_job,
    job_id='new_job',
    cron_expression='0 10 * * *'
)
```

### Adding API Wrapper

```python
# Future: FastAPI endpoint
@app.post("/api/jobs/{job_id}/trigger")
async def trigger_job(job_id: str):
    # Manually trigger job
    pass
```

### Database Integration

```python
# Future: Store job history
class JobHistory:
    timestamp: datetime
    job_id: str
    status: str
    duration: float
```

## Technology Stack Details

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Runtime | Python 3.12 | Application runtime |
| Scheduling | APScheduler 3.10.4 | Job scheduling |
| Locking | fcntl (stdlib) | File locking |
| Slack | slack-sdk 3.33.5 | Slack integration |
| GSheets | gspread 6.2.1 | Google Sheets API |
| Smartsheet | smartsheet-python-sdk 3.0.3 | Smartsheet API |
| Container | Alpine Linux | Minimal image |
| Orchestration | Kubernetes | Container orchestration |

---

**This architecture is designed for:**
- ✅ Reliability (error handling, retries)
- ✅ Scalability (horizontal scaling support)
- ✅ Maintainability (clean separation, documented)
- ✅ Extensibility (easy to add jobs)
- ✅ Observability (comprehensive logging)

