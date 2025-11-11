# Automated AI Agent Reply System

## Overview

The automated reply system listens to customer email replies and intelligently responds based on the customer's intent. It can:
1. **Answer questions** using the AI agent (Text-to-SQL or Document RAG)
2. **Notify sales team** when customers express intent to schedule viewings or sales calls
3. **Nudge customers** towards goal outcomes (property viewing/sales call)

## How It Works

### 1. Email Reply Capture
- When customers reply to campaign emails, the system captures them via IMAP
- Replies are stored as `Conversation` entries with `sender='customer'`

### 2. Intent Classification
- The system uses an LLM-based intent classifier to analyze customer messages
- Two possible intents:
  - **`goal_reached`**: Customer wants to schedule viewing/sales call/meeting
  - **`question`**: Customer is asking questions about properties

### 3. Automated Response

#### If Intent is "goal_reached" (confidence ≥ 0.7):
1. **Notify Sales Team**: Sends email notification to sales team with:
   - Lead information (name, email, phone)
   - Customer's message
   - Goal type (viewing/sales call)
   - Campaign details
2. **Send Acknowledgment**: Sends confirmation email to customer
3. **Mark as Notified**: Sets `sales_team_notified=True` on conversation

#### If Intent is "question":
1. **Use AI Agent**: Routes query through RealEstateAgent:
   - **Text-to-SQL**: For database queries (statistics, counts, lists)
   - **Document RAG**: For property information (amenities, features, specifications)
2. **Generate Response**: Agent retrieves relevant information and synthesizes answer
3. **Add Goal Nudge**: Appends gentle call-to-action encouraging viewing/sales call
4. **Send Reply**: Emails the response to the customer

## Configuration

### Environment Variables

Add to your `.env` file:

```env
# Sales Team Email (for notifications when leads reach goal outcomes)
SALES_TEAM_EMAIL=sales@yourcompany.com

# If not set, defaults to DEFAULT_FROM_EMAIL
```

### Database Fields

The `Conversation` model has been updated with:
- `sales_team_notified`: Boolean flag indicating if sales team was notified
- `auto_reply_processed`: Boolean flag indicating if automated reply was processed

## Usage

### Automatic Processing

When new email replies are captured (via `check_email_replies` command or API), the system automatically:
1. Creates a `Conversation` entry
2. Triggers automated reply processing
3. Sends appropriate response based on intent

### Manual Processing

To manually process pending replies:

```bash
python manage.py process_auto_replies
```

Options:
- `--limit N`: Process maximum N conversations (default: 50)
- `--force`: Reprocess already processed conversations

### Check Email Replies

To check for new email replies and trigger auto-reply:

```bash
python manage.py check_email_replies --days 7
```

Or via API:
```bash
POST /api/campaigns/check-replies?days=7
```

## Intent Classification Details

### Goal Reached Indicators
- "I want to schedule a viewing"
- "Can I book a site visit?"
- "I'd like to speak with a sales representative"
- "When can I visit the property?"
- "Please call me to discuss"
- Strong buying interest with next steps

### Question Indicators
- "What are the amenities?"
- "What's the price range?"
- "Tell me about the location"
- "What unit types are available?"
- General inquiries requiring information retrieval

### Confidence Threshold
- Only processes as "goal_reached" if confidence ≥ 0.7
- Lower confidence defaults to "question" to avoid false positives

## Sales Team Notification

When a lead reaches a goal outcome, the sales team receives an email with:

**Subject**: `🚨 Lead Ready: [Lead Name] - [Goal Type] Request`

**Body includes**:
- Lead information (name, email, phone)
- Project name
- Goal type (Property Viewing / Sales Call / Next Step)
- Customer's original message
- Campaign details

## Customer Acknowledgment

When goal is reached, customer receives:

```
Hi [Name],

Thank you for your interest in [Project]! We've received your request for a [goal] and our sales team will be in touch with you shortly to schedule a convenient time.

In the meantime, if you have any questions, please feel free to reply to this email.

Best regards,
NurturingAI Sales Team
```

## Agent Response Format

When answering questions, the agent:
1. Retrieves relevant information using Text-to-SQL or Document RAG
2. Synthesizes a clear, helpful response
3. Adds a goal nudge at the end:

```
[Agent's answer to the question]

---

I hope this information helps! If you'd like to learn more or schedule a viewing of [Project], please let me know and I'll connect you with our sales team.

Best regards,
NurturingAI
```

## Monitoring

### Check Processing Status

Query conversations to see processing status:

```python
from campaigns.models import Conversation

# Pending auto-reply processing
pending = Conversation.objects.filter(
    sender='customer',
    auto_reply_processed=False
)

# Sales team notified
notified = Conversation.objects.filter(
    sales_team_notified=True
)
```

### Logs

The system logs all processing steps:
- Intent classification results
- Agent tool usage
- Email sending status
- Errors and warnings

Check Django logs for detailed information.

## Troubleshooting

### Auto-reply not processing
1. Check if `auto_reply_processed=False` for customer conversations
2. Run `python manage.py process_auto_replies` manually
3. Check logs for errors

### Sales team not receiving notifications
1. Verify `SALES_TEAM_EMAIL` in `.env` or settings
2. Check email sending configuration
3. Verify email backend is working (test with console backend first)

### Intent misclassification
1. Check confidence scores in logs
2. Adjust confidence threshold in `services/automated_reply_service.py` (currently 0.7)
3. Review intent classification prompt in `services/intent_classifier.py`

## Architecture

### Services

1. **`IntentClassifier`** (`services/intent_classifier.py`):
   - Classifies customer message intent
   - Returns intent, confidence, reasoning, goal_type

2. **`AutomatedReplyService`** (`services/automated_reply_service.py`):
   - Processes customer replies
   - Triggers sales team notifications
   - Generates and sends automated responses
   - Uses RealEstateAgent for question answering

3. **`EmailReplyService`** (`services/email_reply_service.py`):
   - Captures email replies via IMAP
   - Automatically triggers automated reply processing

### Integration Points

- **RealEstateAgent**: Used for answering questions (Text-to-SQL and Document RAG)
- **Email Service**: Sends automated replies and notifications
- **Conversation Model**: Stores all customer-agent interactions

## Future Enhancements

Potential improvements:
- Background task processing (Celery) for better performance
- Configurable confidence thresholds
- Customizable goal nudge messages
- Multi-language support
- WhatsApp integration for automated replies
- Analytics dashboard for intent classification accuracy

