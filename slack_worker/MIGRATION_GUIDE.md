# Migration Guide: Slack Workflows → Slack Worker Service

## Overview

This guide helps you transition from the existing Slack workflows to the new Slack Worker service.

## Current State (Slack Workflows)

**Limitations:**
- ❌ Can only read one release from ROTA sheet
- ❌ Limited automation capabilities
- ❌ No Smartsheet integration
- ❌ Difficult to customize
- ❌ No history/logging

**Current Workflows:**
1. Check release workflow
2. Remind on DM workflow  
3. Remind on group workflow

## New State (Slack Worker Service)

**Benefits:**
- ✅ Reads multiple releases from ROTA sheet
- ✅ Full automation with scheduling
- ✅ Smartsheet to Google Sheets sync
- ✅ Highly customizable via configuration
- ✅ Complete logging and history
- ✅ Horizontally scalable
- ✅ Version controlled

## Migration Steps

### Phase 1: Preparation (Week 1)

#### 1.1 Gather Configuration

Collect the following information from your current setup:

```bash
# Slack Configuration
- Bot Token (from existing bot)
- App Token (from existing bot)
- Channel ID for group notifications
- User ID mappings

# Google Sheets
- Service account credentials
- ROTA sheet name
- Worksheet names

# Smartsheet (if using)
- Access token
- Sheet ID
```

#### 1.2 Set Up Google Sheets Sync Worksheet

The service needs an intermediate worksheet for Smartsheet sync:

1. Open your ROTA Google Sheet
2. Create a new worksheet named "Smartsheet_Sync"
3. The service will auto-populate headers on first run

Alternatively, the service will create it automatically if it doesn't exist.

#### 1.3 Update User Mappings

Create a user mapping JSON with Slack user IDs:

```json
{
  "john.doe": "U12345ABC",
  "jane.smith": "U67890DEF",
  "bob.wilson": "U24680XYZ"
}
```

**How to find Slack User IDs:**
1. In Slack, click on a user's profile
2. Click "More" → "Copy member ID"
3. Or use Slack API: `https://api.slack.com/methods/users.list`

### Phase 2: Development Testing (Week 2)

#### 2.1 Deploy to Development Environment

```bash
# Clone and setup
git pull origin main
cd slack_worker

# Configure for dev
cp .env.example .env
# Edit .env with development values

# Test locally
python -m slack_worker.main
```

#### 2.2 Verify Each Job

**Test Group Reminder:**
```bash
# Set to run every 5 minutes for testing
SCHEDULE_GROUP_REMINDER=*/5 * * * *
ENABLE_GROUP_REMINDER=true
ENABLE_DM_REMINDER=false
ENABLE_SHEET_SYNC=false
```

Wait 5 minutes and verify:
- [ ] Message appears in test channel
- [ ] Release information is correct
- [ ] User mentions work (@username)
- [ ] Multiple releases displayed

**Test DM Reminders:**
```bash
# Enable DM reminders
ENABLE_GROUP_REMINDER=false
ENABLE_DM_REMINDER=true
ENABLE_SHEET_SYNC=false

# Set to run soon (adjust to current day/time)
SCHEDULE_DM_REMINDER_MONDAY=*/10 * * * *
```

Verify:
- [ ] DMs received by test users
- [ ] Correct role information (PM/QE)
- [ ] Release details accurate
- [ ] All assignees notified

**Test Smartsheet Sync:**
```bash
# Enable sheet sync
ENABLE_GROUP_REMINDER=false
ENABLE_DM_REMINDER=false
ENABLE_SHEET_SYNC=true

# Run every 10 minutes
SCHEDULE_SHEET_SYNC=*/10 * * * *
```

Verify:
- [ ] Smartsheet data fetched
- [ ] Google Sheet updated
- [ ] Sync timestamp recorded
- [ ] Leads/members populated

### Phase 3: Parallel Run (Week 3-4)

Run both old Slack workflows AND new service simultaneously:

#### 3.1 Deploy Worker Service to Production

```bash
# Build and push container
docker build -f slack_worker/Dockerfile -t your-registry/slack-worker:v1.0.0 .
docker push your-registry/slack-worker:v1.0.0

# Deploy to Kubernetes/OpenShift
kubectl apply -f slack_worker/k8s/deployment.yaml
```

#### 3.2 Configure Schedules

Set schedules to match or slightly offset from Slack workflows:

```bash
# If Slack workflow runs at 9:00 AM
# Set worker to run at 9:05 AM (5 min offset)
SCHEDULE_GROUP_REMINDER=5 9 * * MON,THU
```

#### 3.3 Monitor Both Systems

For 1-2 weeks:
- [ ] Compare messages from both systems
- [ ] Verify all releases captured
- [ ] Check user notifications match
- [ ] Monitor for errors/issues
- [ ] Validate Smartsheet sync accuracy

**Monitoring Checklist:**

| Date | Slack Workflow | Worker Service | Issues | Notes |
|------|----------------|----------------|--------|-------|
| Mon 1/8 | ✅ Sent | ✅ Sent | None | Both match |
| Thu 1/11 | ✅ Sent | ✅ Sent | None | - |
| ... | | | | |

### Phase 4: Cutover (Week 5)

#### 4.1 Disable Slack Workflows

Once confident in the new service:

1. **Disable Slack workflows:**
   - Open Slack workflow settings
   - Pause or delete the three ROTA workflows
   - Document the workflow configurations (for rollback)

2. **Update documentation:**
   - Update team wiki/docs
   - Notify team of the change
   - Provide new service documentation links

#### 4.2 Adjust Worker Schedules

Remove the offset and use primary schedules:

```bash
# Set to desired production schedules
SCHEDULE_GROUP_REMINDER=0 9 * * MON,THU
SCHEDULE_DM_REMINDER_FRIDAY=0 17 * * FRI
SCHEDULE_DM_REMINDER_MONDAY=0 9 * * MON
SCHEDULE_SHEET_SYNC=0 8 * * *
```

#### 4.3 Enable All Features

```bash
ENABLE_GROUP_REMINDER=true
ENABLE_DM_REMINDER=true
ENABLE_SHEET_SYNC=true
```

### Phase 5: Optimization (Ongoing)

#### 5.1 Fine-tune Schedules

Based on feedback:
- Adjust timing if needed
- Change frequency
- Update timezone if required

#### 5.2 Add Monitoring

Set up monitoring for:
- Job execution success/failure
- Message delivery rates
- Sync errors
- Resource usage

#### 5.3 Scale as Needed

```bash
# Increase replicas if needed
kubectl scale deployment/slack-worker --replicas=3 -n ocp-sustaining-bot
```

## Comparison Matrix

| Feature | Slack Workflows | Worker Service |
|---------|----------------|----------------|
| Multiple releases | ❌ No | ✅ Yes |
| Smartsheet integration | ❌ No | ✅ Yes |
| Customizable schedules | ⚠️ Limited | ✅ Full control |
| Logging/history | ❌ No | ✅ Complete |
| Version control | ❌ No | ✅ Yes |
| Horizontal scaling | ❌ No | ✅ Yes |
| Development testing | ⚠️ Difficult | ✅ Easy |
| Extensibility | ❌ No | ✅ High |
| Cost | Included | Infrastructure |

## Rollback Plan

If issues arise during migration:

### Immediate Rollback (< 1 hour)

```bash
# 1. Disable worker service
kubectl scale deployment/slack-worker --replicas=0 -n ocp-sustaining-bot

# 2. Re-enable Slack workflows
# (Use saved workflow configurations)

# 3. Notify team
```

### Partial Rollback

Disable specific jobs:

```bash
# Disable only problematic job
ENABLE_GROUP_REMINDER=false  # Keep others enabled
kubectl rollout restart deployment/slack-worker -n ocp-sustaining-bot
```

### Data Recovery

- Smartsheet data is read-only (safe)
- Google Sheets sync uses separate worksheet (safe)
- Original ROTA data remains unchanged

## Troubleshooting During Migration

### Issue: Worker sends duplicate messages

**Cause:** Both workflow and worker running at same time

**Solution:**
```bash
# Option 1: Offset schedules more
SCHEDULE_GROUP_REMINDER=15 9 * * MON,THU  # 15 min after workflow

# Option 2: Disable workflow immediately
```

### Issue: Missing releases in worker messages

**Cause:** Google Sheet data not formatted correctly

**Solution:**
1. Check column names in Assignment worksheet
2. Verify "This Week"/"Next Week" values in Activity column
3. Check date formats (YYYY-MM-DD)

### Issue: Users not receiving DMs

**Cause:** User ID mapping incorrect

**Solution:**
```bash
# Verify user IDs
# In .env, update ROTA_USERS with correct Slack user IDs
ROTA_USERS='{"john.doe":"U_CORRECT_ID"}'
```

### Issue: Smartsheet sync failing

**Cause:** Invalid credentials or sheet ID

**Solution:**
1. Verify `SMARTSHEET_ACCESS_TOKEN` is valid
2. Check `SMARTSHEET_SHEET_ID` is correct
3. Ensure sheet has required columns (Release, Start Date, End Date)
4. Review logs for specific error

## Testing Checklist

Before going live:

### Functionality Tests
- [ ] Group reminder sends to correct channel
- [ ] All current week releases included
- [ ] Next week releases included (Monday only)
- [ ] User mentions resolve correctly
- [ ] DM reminders reach all assignees
- [ ] PM and QE roles identified correctly
- [ ] Smartsheet data fetched successfully
- [ ] Google Sheet updated with sync data
- [ ] Multiple releases handled correctly

### Configuration Tests
- [ ] Jobs run at scheduled times
- [ ] Timezone handled correctly
- [ ] Enable/disable flags work
- [ ] Schedule changes take effect
- [ ] Lock files created correctly

### Scale Tests
- [ ] Multiple pods don't duplicate jobs
- [ ] Lock mechanism prevents double execution
- [ ] Pods can be scaled up/down safely

### Error Handling Tests
- [ ] Graceful handling of missing releases
- [ ] Proper error messages in logs
- [ ] Recovery from API failures
- [ ] Handles empty/malformed data

## Communication Plan

### Pre-Migration Announcement

**To:** Engineering team  
**When:** 1 week before

```
Subject: Upcoming ROTA Reminder System Update

Team,

We're migrating from Slack workflows to a new automated service for ROTA reminders.

What's changing:
- Better support for multiple releases
- Automatic Smartsheet integration
- More reliable scheduling

When: Starting [DATE]

What you'll notice:
- Same reminders, improved reliability
- Possible slight timing changes
- Better formatting

Questions? Contact: [YOUR NAME/TEAM]
```

### Post-Migration Announcement

**To:** Engineering team  
**When:** After successful cutover

```
Subject: ROTA Reminder System Migration Complete

Team,

The new ROTA reminder system is now live!

New features:
✅ Handles multiple releases per week
✅ Automated Smartsheet sync
✅ Improved reliability

If you notice any issues, please report to: [CONTACT]

Documentation: [LINK TO README]
```

## Success Metrics

Track these metrics for 30 days post-migration:

| Metric | Target | Actual |
|--------|--------|--------|
| Job execution success rate | >99% | ___ |
| Message delivery rate | 100% | ___ |
| User complaints | <5 | ___ |
| Sync errors | 0 | ___ |
| Duplicate notifications | 0 | ___ |

## Timeline Summary

| Week | Phase | Activities |
|------|-------|-----------|
| 1 | Preparation | Gather config, setup dev environment |
| 2 | Dev Testing | Test all jobs individually |
| 3-4 | Parallel Run | Run both systems, monitor closely |
| 5 | Cutover | Disable workflows, enable full service |
| 6+ | Optimization | Monitor, tune, scale as needed |

## Support During Migration

- **Slack Channel:** #ocp-sustaining-support
- **On-call:** [NAME/CONTACT]
- **Documentation:** slack_worker/README.md
- **Logs:** `kubectl logs -f deployment/slack-worker`

---

**Questions or concerns?** Open an issue or contact the sustaining team.

