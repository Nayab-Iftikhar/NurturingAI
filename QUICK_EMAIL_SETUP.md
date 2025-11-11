# Quick Email Setup Guide

## Problem: Not Receiving Emails

The system is currently using **Console Email Backend**, which means emails are only printed to the terminal, not actually sent.

## Solution: Enable SMTP Email Sending

### Step 1: Create/Update `.env` file

Create a `.env` file in the project root (same directory as `manage.py`) with the following content:

```env
# Change to SMTP backend to send real emails
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend

# Gmail SMTP Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=nayabiftikhar6633@gmail.com
EMAIL_HOST_PASSWORD=your-app-password-here

# Test email (all emails will be sent here)
TEST_EMAIL=nayabiftikhar6633@gmail.com
DEFAULT_FROM_EMAIL=nayabiftikhar6633@gmail.com
```

### Step 2: Get Gmail App Password

Since you're using Gmail (`nayabiftikhar6633@gmail.com`), you need to generate an App Password:

1. **Enable 2-Step Verification** (if not already enabled):
   - Go to https://myaccount.google.com/security
   - Under "How you sign in to Google", click "2-Step Verification"
   - Follow the steps to enable it

2. **Generate App Password**:
   - Go to https://myaccount.google.com/apppasswords
   - Select "Mail" as the app
   - Select "Other (Custom name)" as the device
   - Enter "NurturingAI" as the name
   - Click "Generate"
   - Copy the 16-character password (it will look like: `abcd efgh ijkl mnop`)

3. **Update `.env` file**:
   - Replace `your-app-password-here` with the 16-character password (remove spaces)
   - Example: `EMAIL_HOST_PASSWORD=abcdefghijklmnop`

### Step 3: Restart Django Server

After updating the `.env` file, **restart your Django server**:

```bash
# Stop the current server (Ctrl+C)
# Then restart it
python manage.py runserver
```

### Step 4: Test Email Sending

1. Go to your application
2. Create a campaign or generate messages
3. Check your inbox at `nayabiftikhar6633@gmail.com`

## Troubleshooting

### Still not receiving emails?

1. **Check terminal output**: Look for any error messages when sending emails
2. **Verify App Password**: Make sure you're using the App Password, not your regular Gmail password
3. **Check spam folder**: Emails might be in spam/junk folder
4. **Verify settings**: Run this command to check current settings:
   ```bash
   python manage.py shell
   >>> from django.conf import settings
   >>> print("EMAIL_BACKEND:", settings.EMAIL_BACKEND)
   >>> print("EMAIL_HOST_USER:", settings.EMAIL_HOST_USER)
   >>> print("EMAIL_HOST:", settings.EMAIL_HOST)
   ```

### Common Errors

**"SMTPAuthenticationError"**:
- Make sure you're using an App Password, not your regular password
- Verify 2-Step Verification is enabled

**"Connection refused"**:
- Check your internet connection
- Verify EMAIL_HOST and EMAIL_PORT are correct

**"Email sent but not received"**:
- Check spam/junk folder
- Verify TEST_EMAIL is correct
- Check if emails are being blocked by Gmail

## Alternative: Use Console Backend for Testing

If you just want to see emails in the terminal (for testing), you can keep the console backend:

```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

Emails will appear in the terminal where you run `python manage.py runserver`.

