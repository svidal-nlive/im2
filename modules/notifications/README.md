# Notifications Service

This service manages the notification system for the IM2 platform, handling all event notifications across multiple channels.

## Features

- Event reception from all pipeline services
- Multi-channel delivery (email, webhooks, UI)
- Templating and internationalization
- Rate limiting and deduplication
- Retry and backoff mechanisms
- User preference management
- Audit logging and history

## Channels Supported

- Email (SMTP)
- In-app UI notifications
- Webhooks
- PagerDuty/OpsGenie integration
- Slack/Discord (configurable)

## Configuration

The service is configured through environment variables:

```
# General
LOG_LEVEL=INFO
DEBUG=false

# Redis
REDIS_URL=redis://redis:6379/0

# SMTP Config
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=notifications@example.com
SMTP_PASSWORD=password
SMTP_FROM=IM2 <notifications@example.com>
SMTP_USE_TLS=true

# Webhook Config
WEBHOOK_TIMEOUT_SECONDS=5
MAX_RETRIES=3
RETRY_DELAY_SECONDS=60

# Rate Limiting
RATE_LIMIT_PER_USER=10
RATE_LIMIT_WINDOW_MINUTES=5

# PagerDuty
PAGERDUTY_API_KEY=
PAGERDUTY_SERVICE_ID=

# Slack
SLACK_WEBHOOK_URL=
```

## Event Types

The service handles the following event types:

- `job.completed` - Job processing completed successfully
- `job.failed` - Job failed with error
- `job.progress` - Job progress update
- `system.error` - System-level error
- `system.warning` - System-level warning
- `quota.exceeded` - User quota exceeded
- `quota.approaching` - User quota approaching limit

## API Endpoints

### Health Check

```
GET /health
```

Returns health status of the notification service.

### Metrics

```
GET /metrics
```

Returns metrics for the notification service including:
- Notification counts by type and channel
- Delivery success/failure rates
- Average delivery time
- Rate limit hits

### User Preferences

```
GET /preferences/:user_id
```

Get notification preferences for a user.

```
PUT /preferences/:user_id
```

Update notification preferences for a user.

### Notification History

```
GET /history/:user_id
```

Get notification history for a user.

## Development

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run service:
   ```
   python main.py
   ```

## Testing

Run unit tests:
```
pytest
```

Run integration tests (requires Redis):
```
pytest --integration
```
