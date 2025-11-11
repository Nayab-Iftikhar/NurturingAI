# Email Setup Guide

## Current Configuration

The system is currently configured to use **Console Email Backend** for development. This means emails are printed to the terminal/console where Django is running, not actually sent via email.

## Viewing Emails (Current Setup)

When you generate and send campaign messages, the emails will appear in the **terminal/console** where you're running `python manage.py runserver`. Look for output like:

```
EMAIL SENT (Console Backend - Check terminal output)
================================================================================
To: nayabiftikhar6633@gmail.com
From: nayabiftikhar6633@gmail.com
Subject: Exciting Opportunities at [Project Name]
--------------------------------------------------------------------------------
[Email content here]
================================================================================
```

## To Send Real Emails

To actually send emails via SMTP, you need to:

### 1. Update `.env` file

Create or update your `.env` file with SMTP settings:

```env
# Change email backend to SMTP
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend

# SMTP Configuration (Gmail example)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Test email (all emails will be sent here)
TEST_EMAIL=nayabiftikhar6633@gmail.com
DEFAULT_FROM_EMAIL=your-email@gmail.com
```

### 2. Gmail Setup (if using Gmail)

1. Enable 2-Factor Authentication on your Gmail account
2. Generate an App Password:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate a password for "Mail"
   - Use this password in `EMAIL_HOST_PASSWORD`

### 3. Other Email Providers

**Outlook/Hotmail:**
```env
EMAIL_HOST=smtp-mail.outlook.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
```

**SendGrid:**
```env
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=your-sendgrid-api-key
```

**Mailgun:**
```env
EMAIL_HOST=smtp.mailgun.org
EMAIL_PORT=587
EMAIL_HOST_USER=your-mailgun-username
EMAIL_HOST_PASSWORD=your-mailgun-password
```

### 4. Restart Django Server

After updating `.env`, restart your Django server:
```bash
python manage.py runserver
```

## Testing Email Configuration

You can test your email setup by:

1. Creating a campaign
2. Generating and sending messages
3. Checking your email inbox (or console output if using console backend)

## 3. Capturing Email Replies

The system can automatically capture email replies using IMAP. To enable this feature:

1. **Update your `.env` file** with IMAP settings:
   ```env
   # IMAP Configuration (for capturing email replies)
   IMAP_HOST=imap.gmail.com
   IMAP_PORT=993
   IMAP_USE_SSL=True
   IMAP_USER=your-email@gmail.com  # Same as EMAIL_HOST_USER
   IMAP_PASSWORD=your-app-password  # Same as EMAIL_HOST_PASSWORD (use App Password for Gmail)
   IMAP_MAILBOX=INBOX
   ```

2. **Check for replies manually**:
   ```bash
   python manage.py check_email_replies --days 7
   ```

3. **Or trigger via API**:
   ```bash
   POST /api/campaigns/check-replies?days=7
   ```

4. **Set up automated checking** (optional):
   You can set up a cron job or scheduled task to run the management command periodically:
   ```bash
   # Run every hour
   0 * * * * cd /path/to/project && python manage.py check_email_replies --days 1
   ```

### How It Works

- When emails are sent, a unique `Message-ID` header is generated and stored in the database
- The reply checking service connects to your IMAP inbox and looks for emails with `In-Reply-To` headers
- When a reply is found, it matches it to the original email using the `Message-ID`
- The reply is automatically stored as a `Conversation` entry with `sender='customer'`
- Replies are displayed in the Conversations page in the frontend

### Important Notes

- **Console Backend (Current)**: Emails are printed to terminal - no actual emails sent
- **SMTP Backend**: Emails are actually sent via email server
- All emails are redirected to `TEST_EMAIL` (nayabiftikhar6633@gmail.com) regardless of the lead's actual email address
- The original recipient's email is included in the message body for reference

