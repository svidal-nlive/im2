import os
import json
import logging
import asyncio
import uuid
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union

import redis.asyncio as redis
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import httpx
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, EmailStr

# Import shared base service class
import sys
sys.path.append('/app')
from base_service import BaseService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("notifications-service")

# Models
class NotificationEvent(BaseModel):
    event_type: str
    severity: str = "info"  # info, warning, error, critical
    source: str
    job_uuid: Optional[str] = None
    user_id: Optional[str] = None
    title: str
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class UserPreference(BaseModel):
    user_id: str
    email_enabled: bool = True
    webhook_enabled: bool = False
    webhook_url: Optional[str] = None
    ui_enabled: bool = True
    pagerduty_enabled: bool = False
    slack_enabled: bool = False
    event_types: List[str] = ["job.completed", "job.failed", "system.error"]
    
class NotificationRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event: NotificationEvent
    channels: List[str]
    status: str = "pending"  # pending, sent, failed, retrying
    attempts: int = 0
    last_attempt: Optional[datetime] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# Service class
class NotificationsService(BaseService):
    def __init__(self):
        super().__init__(service_name="notifications")
        
        # Redis connection
        self.redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        self.redis_client = None
        
        # SMTP settings
        self.smtp_host = os.environ.get("SMTP_HOST", "smtp.example.com")
        self.smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        self.smtp_username = os.environ.get("SMTP_USERNAME", "")
        self.smtp_password = os.environ.get("SMTP_PASSWORD", "")
        self.smtp_from = os.environ.get("SMTP_FROM", "IM2 <notifications@example.com>")
        self.smtp_use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() == "true"
        
        # Webhook settings
        self.webhook_timeout = int(os.environ.get("WEBHOOK_TIMEOUT_SECONDS", "5"))
        self.max_retries = int(os.environ.get("MAX_RETRIES", "3"))
        self.retry_delay = int(os.environ.get("RETRY_DELAY_SECONDS", "60"))
        
        # Rate limiting
        self.rate_limit_per_user = int(os.environ.get("RATE_LIMIT_PER_USER", "10"))
        self.rate_limit_window = int(os.environ.get("RATE_LIMIT_WINDOW_MINUTES", "5"))
        
        # PagerDuty
        self.pagerduty_api_key = os.environ.get("PAGERDUTY_API_KEY", "")
        self.pagerduty_service_id = os.environ.get("PAGERDUTY_SERVICE_ID", "")
        
        # Slack
        self.slack_webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "")
        
        # Templates
        self.templates = {}
        self.load_templates()
        
        # Setup additional routes
        self.setup_routes()
        
        # Metrics
        self.metrics_data = {
            "events_received": 0,
            "notifications_sent": 0,
            "notifications_failed": 0,
            "rate_limited": 0,
            "channel_stats": {
                "email": {"sent": 0, "failed": 0},
                "webhook": {"sent": 0, "failed": 0},
                "ui": {"sent": 0, "failed": 0},
                "pagerduty": {"sent": 0, "failed": 0},
                "slack": {"sent": 0, "failed": 0},
            }
        }
        
        # Start background tasks
        self.app.on_event("startup")(self.startup_event)
        self.app.on_event("shutdown")(self.shutdown_event)
    
    def setup_routes(self):
        """Setup additional routes for the service"""
        self.app.post("/events", response_model=dict)(self.receive_event)
        self.app.get("/preferences/{user_id}", response_model=UserPreference)(self.get_user_preferences)
        self.app.put("/preferences/{user_id}", response_model=UserPreference)(self.update_user_preferences)
        self.app.get("/history/{user_id}", response_model=List[NotificationRecord])(self.get_notification_history)
    
    def load_templates(self):
        """Load notification templates"""
        # Default templates
        self.templates = {
            "email": {
                "job.completed": {
                    "subject": "IM2: Job Completed Successfully",
                    "body": "Your job {job_uuid} has completed successfully. You can now access your processed files."
                },
                "job.failed": {
                    "subject": "IM2: Job Failed",
                    "body": "Your job {job_uuid} has failed with error: {message}"
                },
                "system.error": {
                    "subject": "IM2: System Error",
                    "body": "A system error has occurred: {message}"
                }
            },
            "ui": {
                "job.completed": {
                    "title": "Job Completed",
                    "body": "Your job has completed successfully."
                },
                "job.failed": {
                    "title": "Job Failed",
                    "body": "Your job has failed with error: {message}"
                },
                "system.error": {
                    "title": "System Error",
                    "body": "A system error has occurred: {message}"
                }
            }
        }
        
        # TODO: Load custom templates from files if available
    
    async def startup_event(self):
        """Startup tasks"""
        # Connect to Redis
        self.redis_client = redis.Redis.from_url(self.redis_url)
        
        # Start background tasks
        asyncio.create_task(self.event_listener())
        asyncio.create_task(self.retry_failed_notifications())
    
    async def shutdown_event(self):
        """Shutdown tasks"""
        # Close Redis connection
        if self.redis_client:
            await self.redis_client.close()
    
    async def event_listener(self):
        """Listen for events on Redis pub/sub"""
        try:
            # Subscribe to the notifications channel
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe("im2:notifications")
            
            logger.info("Started event listener")
            
            # Listen for messages
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        event = NotificationEvent(**data)
                        await self.process_event(event)
                    except Exception as e:
                        logger.error(f"Error processing event: {str(e)}")
        except Exception as e:
            logger.error(f"Error in event listener: {str(e)}")
            # Reconnect after a delay
            await asyncio.sleep(5)
            asyncio.create_task(self.event_listener())
    
    async def retry_failed_notifications(self):
        """Retry failed notifications"""
        while True:
            try:
                # Get failed notifications that need retry
                now = datetime.utcnow()
                retry_cutoff = now - timedelta(seconds=self.retry_delay)
                
                # Scan for notifications that need retry
                keys = []
                cursor = 0
                pattern = "notifications:failed:*"
                
                while True:
                    cursor, partial_keys = await self.redis_client.scan(cursor, match=pattern)
                    keys.extend(partial_keys)
                    if cursor == 0:
                        break
                
                for key in keys:
                    notification_data = await self.redis_client.get(key)
                    if notification_data:
                        notification = NotificationRecord.parse_raw(notification_data)
                        
                        # Check if it's time to retry
                        if (notification.last_attempt is None or 
                            notification.last_attempt < retry_cutoff):
                            
                            # If we haven't exceeded max retries
                            if notification.attempts < self.max_retries:
                                # Update notification
                                notification.status = "retrying"
                                notification.attempts += 1
                                notification.last_attempt = now
                                notification.updated_at = now
                                
                                # Save updated notification
                                await self.redis_client.set(
                                    key, 
                                    notification.json(),
                                    ex=86400  # TTL: 1 day
                                )
                                
                                # Process the notification
                                await self.send_notification(notification)
            except Exception as e:
                logger.error(f"Error in retry task: {str(e)}")
            
            # Sleep before next retry check
            await asyncio.sleep(30)
    
    async def receive_event(self, event: NotificationEvent, background_tasks: BackgroundTasks):
        """API endpoint to receive events"""
        self.metrics_data["events_received"] += 1
        background_tasks.add_task(self.process_event, event)
        return {"status": "accepted", "event_id": str(uuid.uuid4())}
    
    async def get_user_preferences(self, user_id: str):
        """Get user notification preferences"""
        pref_key = f"preferences:{user_id}"
        pref_data = await self.redis_client.get(pref_key)
        
        if pref_data:
            return UserPreference.parse_raw(pref_data)
        else:
            # Return default preferences
            return UserPreference(user_id=user_id)
    
    async def update_user_preferences(self, user_id: str, preferences: UserPreference):
        """Update user notification preferences"""
        pref_key = f"preferences:{user_id}"
        await self.redis_client.set(pref_key, preferences.json())
        return preferences
    
    async def get_notification_history(self, user_id: str, limit: int = 50):
        """Get notification history for a user"""
        history = []
        keys = []
        cursor = 0
        pattern = f"notifications:*:{user_id}:*"
        
        while True:
            cursor, partial_keys = await self.redis_client.scan(cursor, match=pattern)
            keys.extend(partial_keys)
            if cursor == 0 or len(keys) >= limit:
                break
        
        # Sort keys by creation time (newest first)
        for key in keys[:limit]:
            notification_data = await self.redis_client.get(key)
            if notification_data:
                notification = NotificationRecord.parse_raw(notification_data)
                history.append(notification)
        
        # Sort by created_at (newest first)
        history.sort(key=lambda x: x.created_at, reverse=True)
        return history
    
    async def process_event(self, event: NotificationEvent):
        """Process a notification event"""
        try:
            logger.info(f"Processing event: {event.event_type} from {event.source}")
            
            # If the event has a user_id, check their preferences
            channels = ["ui"]  # Default to UI only
            user_prefs = None
            
            if event.user_id:
                user_prefs = await self.get_user_preferences(event.user_id)
                
                # Only notify if the user wants this event type
                if event.event_type not in user_prefs.event_types:
                    logger.info(f"User {event.user_id} opted out of {event.event_type} notifications")
                    return
                
                # Determine channels based on user preferences
                channels = []
                if user_prefs.email_enabled:
                    channels.append("email")
                if user_prefs.webhook_enabled and user_prefs.webhook_url:
                    channels.append("webhook")
                if user_prefs.ui_enabled:
                    channels.append("ui")
                if user_prefs.pagerduty_enabled and event.severity in ["error", "critical"]:
                    channels.append("pagerduty")
                if user_prefs.slack_enabled:
                    channels.append("slack")
            
            # For critical system events, ensure proper channels
            if event.severity == "critical" and event.event_type.startswith("system."):
                # Always include PagerDuty for critical system events
                if "pagerduty" not in channels and self.pagerduty_api_key:
                    channels.append("pagerduty")
                
                # Always include Slack for critical system events
                if "slack" not in channels and self.slack_webhook_url:
                    channels.append("slack")
            
            # Check rate limiting for the user
            if event.user_id and await self.is_rate_limited(event.user_id):
                logger.warning(f"Rate limiting notifications for user {event.user_id}")
                self.metrics_data["rate_limited"] += 1
                
                # If rate limited, only keep critical notifications
                if event.severity != "critical":
                    return
            
            # Create notification record
            notification = NotificationRecord(
                event=event,
                channels=channels,
                status="pending"
            )
            
            # Store the notification
            notification_key = f"notifications:{notification.id}"
            await self.redis_client.set(
                notification_key, 
                notification.json(),
                ex=86400  # TTL: 1 day
            )
            
            # Add to user's history if applicable
            if event.user_id:
                history_key = f"notifications:history:{event.user_id}:{notification.id}"
                await self.redis_client.set(
                    history_key, 
                    notification.json(),
                    ex=604800  # TTL: 7 days
                )
            
            # Send the notification
            await self.send_notification(notification)
            
        except Exception as e:
            logger.error(f"Error processing event: {str(e)}")
    
    async def is_rate_limited(self, user_id: str) -> bool:
        """Check if a user is rate limited"""
        rate_key = f"rate_limit:{user_id}"
        count = await self.redis_client.get(rate_key)
        
        if count is None:
            # First notification in this window
            await self.redis_client.set(
                rate_key, 
                "1", 
                ex=self.rate_limit_window * 60
            )
            return False
        
        count = int(count)
        if count >= self.rate_limit_per_user:
            return True
        
        # Increment count
        await self.redis_client.incr(rate_key)
        return False
    
    async def send_notification(self, notification: NotificationRecord):
        """Send a notification through all channels"""
        success = True
        errors = []
        
        for channel in notification.channels:
            try:
                if channel == "email":
                    await self.send_email_notification(notification)
                elif channel == "webhook":
                    await self.send_webhook_notification(notification)
                elif channel == "ui":
                    await self.send_ui_notification(notification)
                elif channel == "pagerduty":
                    await self.send_pagerduty_notification(notification)
                elif channel == "slack":
                    await self.send_slack_notification(notification)
                
                # Update metrics
                self.metrics_data["channel_stats"][channel]["sent"] += 1
            except Exception as e:
                logger.error(f"Error sending {channel} notification: {str(e)}")
                errors.append(f"{channel}: {str(e)}")
                success = False
                
                # Update metrics
                self.metrics_data["channel_stats"][channel]["failed"] += 1
        
        # Update notification status
        notification.last_attempt = datetime.utcnow()
        notification.updated_at = datetime.utcnow()
        
        if success:
            notification.status = "sent"
            self.metrics_data["notifications_sent"] += 1
            
            # Store the updated notification
            notification_key = f"notifications:{notification.id}"
            await self.redis_client.set(
                notification_key, 
                notification.json(),
                ex=86400  # TTL: 1 day
            )
        else:
            notification.status = "failed"
            notification.error = "; ".join(errors)
            self.metrics_data["notifications_failed"] += 1
            
            # Store the failed notification for retry
            failed_key = f"notifications:failed:{notification.id}"
            await self.redis_client.set(
                failed_key, 
                notification.json(),
                ex=86400  # TTL: 1 day
            )
    
    async def send_email_notification(self, notification: NotificationRecord):
        """Send an email notification"""
        if not notification.event.user_id:
            raise ValueError("Cannot send email without user_id")
        
        # TODO: Get user email from a user service
        # For now, we'll just use a placeholder
        user_email = f"{notification.event.user_id}@example.com"
        
        # Get template
        event_type = notification.event.event_type
        if event_type not in self.templates["email"]:
            event_type = "system.error"  # Fallback template
        
        template = self.templates["email"][event_type]
        
        # Format subject and body
        subject = template["subject"].format(**notification.event.dict())
        body = template["body"].format(**notification.event.dict())
        
        # Create message
        message = MIMEMultipart()
        message["From"] = self.smtp_from
        message["To"] = user_email
        message["Subject"] = subject
        
        # Add body
        message.attach(MIMEText(body, "plain"))
        
        # Send email
        try:
            smtp = aiosmtplib.SMTP(
                hostname=self.smtp_host,
                port=self.smtp_port,
                use_tls=self.smtp_use_tls
            )
            await smtp.connect()
            
            if self.smtp_username and self.smtp_password:
                await smtp.login(self.smtp_username, self.smtp_password)
            
            await smtp.send_message(message)
            await smtp.quit()
            
            logger.info(f"Email sent to {user_email}")
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            raise
    
    async def send_webhook_notification(self, notification: NotificationRecord):
        """Send a webhook notification"""
        user_prefs = await self.get_user_preferences(notification.event.user_id)
        if not user_prefs.webhook_url:
            raise ValueError("No webhook URL configured")
        
        # Create payload
        payload = {
            "id": notification.id,
            "event_type": notification.event.event_type,
            "severity": notification.event.severity,
            "source": notification.event.source,
            "title": notification.event.title,
            "message": notification.event.message,
            "timestamp": notification.event.timestamp.isoformat(),
            "data": notification.event.data
        }
        
        if notification.event.job_uuid:
            payload["job_uuid"] = notification.event.job_uuid
        
        # Send webhook
        async with httpx.AsyncClient(timeout=self.webhook_timeout) as client:
            response = await client.post(
                user_prefs.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code >= 400:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Webhook failed with status {response.status_code}"
                )
            
            logger.info(f"Webhook sent to {user_prefs.webhook_url}")
    
    async def send_ui_notification(self, notification: NotificationRecord):
        """Send a UI notification"""
        if not notification.event.user_id:
            # For system-wide UI notifications
            channel = "im2:ui:notifications:system"
        else:
            channel = f"im2:ui:notifications:{notification.event.user_id}"
        
        # Get template
        event_type = notification.event.event_type
        if event_type not in self.templates["ui"]:
            event_type = "system.error"  # Fallback template
        
        template = self.templates["ui"][event_type]
        
        # Format title and body
        title = template["title"].format(**notification.event.dict())
        body = template["body"].format(**notification.event.dict())
        
        # Create payload
        payload = {
            "id": notification.id,
            "event_type": notification.event.event_type,
            "severity": notification.event.severity,
            "title": title,
            "message": body,
            "timestamp": notification.event.timestamp.isoformat()
        }
        
        if notification.event.job_uuid:
            payload["job_uuid"] = notification.event.job_uuid
        
        # Publish to Redis
        await self.redis_client.publish(channel, json.dumps(payload))
        logger.info(f"UI notification sent to channel {channel}")
    
    async def send_pagerduty_notification(self, notification: NotificationRecord):
        """Send a PagerDuty notification"""
        if not self.pagerduty_api_key or not self.pagerduty_service_id:
            raise ValueError("PagerDuty not configured")
        
        # Map severity
        severity_map = {
            "info": "info",
            "warning": "warning",
            "error": "error",
            "critical": "critical"
        }
        
        # Create payload
        payload = {
            "routing_key": self.pagerduty_api_key,
            "event_action": "trigger",
            "payload": {
                "summary": notification.event.title,
                "severity": severity_map.get(notification.event.severity, "error"),
                "source": notification.event.source,
                "custom_details": {
                    "message": notification.event.message,
                    "event_type": notification.event.event_type
                }
            }
        }
        
        if notification.event.job_uuid:
            payload["payload"]["custom_details"]["job_uuid"] = notification.event.job_uuid
        
        if notification.event.data:
            payload["payload"]["custom_details"].update(notification.event.data)
        
        # Send to PagerDuty
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                "https://events.pagerduty.com/v2/enqueue",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code >= 400:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"PagerDuty API failed with status {response.status_code}"
                )
            
            logger.info("PagerDuty alert sent")
    
    async def send_slack_notification(self, notification: NotificationRecord):
        """Send a Slack notification"""
        if not self.slack_webhook_url:
            raise ValueError("Slack webhook not configured")
        
        # Map severity to color
        color_map = {
            "info": "#36a64f",      # Green
            "warning": "#f2c744",   # Yellow
            "error": "#d63232",     # Red
            "critical": "#7b0000"   # Dark red
        }
        
        # Create payload
        payload = {
            "attachments": [
                {
                    "color": color_map.get(notification.event.severity, "#36a64f"),
                    "title": notification.event.title,
                    "text": notification.event.message,
                    "fields": [
                        {
                            "title": "Source",
                            "value": notification.event.source,
                            "short": True
                        },
                        {
                            "title": "Event Type",
                            "value": notification.event.event_type,
                            "short": True
                        },
                        {
                            "title": "Severity",
                            "value": notification.event.severity,
                            "short": True
                        }
                    ],
                    "ts": int(time.time())
                }
            ]
        }
        
        # Add job_uuid if available
        if notification.event.job_uuid:
            payload["attachments"][0]["fields"].append({
                "title": "Job UUID",
                "value": notification.event.job_uuid,
                "short": True
            })
        
        # Send to Slack
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                self.slack_webhook_url,
                json=payload
            )
            
            if response.status_code >= 400:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Slack webhook failed with status {response.status_code}"
                )
            
            logger.info("Slack notification sent")
    
    async def metrics(self):
        """Override metrics to include notification statistics"""
        base_metrics = await super().metrics()
        
        # Add notification metrics
        notification_metrics = {
            "events_received": self.metrics_data["events_received"],
            "notifications_sent": self.metrics_data["notifications_sent"],
            "notifications_failed": self.metrics_data["notifications_failed"],
            "rate_limited": self.metrics_data["rate_limited"],
            "channel_stats": self.metrics_data["channel_stats"]
        }
        
        # Merge metrics
        merged_metrics = {**base_metrics, **notification_metrics}
        return merged_metrics

# Create service instance
service = NotificationsService()
app = service.app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
