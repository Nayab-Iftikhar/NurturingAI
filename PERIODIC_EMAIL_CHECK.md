# Periodic Email Reply Checking

## Overview

The system now supports automatic periodic checking for email replies every minute, and also checks for new replies when viewing a conversation.

## Features

### 1. Periodic Checking (Every Minute)

A new management command `check_email_replies_periodic` can run continuously, checking for new email replies every minute.

#### Usage

**Continuous Mode** (runs until stopped):
```bash
python manage.py check_email_replies_periodic
```

**Single Run Mode** (for cron jobs):
```bash
python manage.py check_email_replies_periodic --once
```

**Custom Interval**:
```bash
python manage.py check_email_replies_periodic --interval 30  # Check every 30 seconds
```

**Custom Days to Check**:
```bash
python manage.py check_email_replies_periodic --days 2  # Check last 2 days
```

#### Options

- `--once`: Run once and exit (useful for cron jobs)
- `--interval N`: Interval in seconds between checks (default: 60)
- `--days N`: Number of days to look back for emails (default: 1)

### 2. Automatic Check on Conversation View

When viewing a conversation in the frontend, the system automatically checks for new email replies before displaying the conversation. This ensures users always see the latest replies.

**How it works:**
- When `GET /api/agent/queries?campaign_lead_id={id}` is called
- The system checks for new replies from the last 7 days (or since last message sent)
- New replies are captured and processed automatically
- The conversation is then displayed with all latest messages

## Setup for Production

### Option 1: Cron Job (Recommended)

Add to your crontab to run every minute:

```bash
* * * * * cd /path/to/NurturingAI && /path/to/venv/bin/python manage.py check_email_replies_periodic --once --days 1
```

### Option 2: Systemd Timer (Linux)

Create `/etc/systemd/system/nurturingai-email-check.service`:
```ini
[Unit]
Description=NurturingAI Email Reply Checker
After=network.target

[Service]
Type=oneshot
User=your-user
WorkingDirectory=/path/to/NurturingAI
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python manage.py check_email_replies_periodic --once --days 1
```

Create `/etc/systemd/system/nurturingai-email-check.timer`:
```ini
[Unit]
Description=Run NurturingAI Email Checker every minute
Requires=nurturingai-email-check.service

[Timer]
OnCalendar=*:0/1
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start:
```bash
sudo systemctl enable nurturingai-email-check.timer
sudo systemctl start nurturingai-email-check.timer
```

### Option 3: Background Process

Run as a background process (for development/testing):

```bash
nohup python manage.py check_email_replies_periodic > email_check.log 2>&1 &
```

### Option 4: Celery (Advanced)

For production environments with Celery:

```python
# tasks.py
from celery import shared_task
from services.email_reply_service import check_email_replies

@shared_task
def check_email_replies_task():
    return check_email_replies(days=1)
```

```python
# celerybeat_schedule in settings.py
CELERY_BEAT_SCHEDULE = {
    'check-email-replies': {
        'task': 'tasks.check_email_replies_task',
        'schedule': 60.0,  # Every 60 seconds
    },
}
```

## Monitoring

### Check Logs

The periodic checker logs all activity:
- New replies found
- Errors encountered
- Processing statistics

### Check Status

View pending conversations that haven't been processed:
```python
from campaigns.models import Conversation

pending = Conversation.objects.filter(
    sender='customer',
    auto_reply_processed=False
).count()
```

## Troubleshooting

### Replies not being captured

1. **Check IMAP configuration**: Verify `IMAP_USER` and `IMAP_PASSWORD` in `.env`
2. **Check periodic process**: Ensure the periodic checker is running
3. **Check logs**: Look for errors in Django logs or email check log file
4. **Manual check**: Run `python manage.py check_email_replies --days 7` manually

### High CPU/Memory Usage

If checking every minute is too frequent:
- Increase interval: `--interval 300` (5 minutes)
- Reduce days to check: `--days 1` (only last day)
- Use cron job instead of continuous mode

### Missing Replies

If replies are not appearing:
1. Check if periodic process is running
2. Verify IMAP credentials are correct
3. Check email server logs for connection issues
4. Manually trigger: `python manage.py check_email_replies --days 7`

## Best Practices

1. **Production**: Use cron job or systemd timer (Option 1 or 2)
2. **Development**: Use continuous mode or manual checks
3. **Monitoring**: Set up log monitoring for errors
4. **Backup**: Keep IMAP credentials secure and backed up
5. **Testing**: Test with `--once` flag before setting up cron

## Integration with Auto-Reply

When new replies are captured:
1. Email reply is stored as `Conversation` entry
2. Automated reply service processes the reply
3. Intent is classified (goal_reached vs question)
4. Appropriate response is sent automatically

See `AUTOMATED_REPLY_SYSTEM.md` for details on automated responses.

