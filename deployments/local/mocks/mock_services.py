"""
Mock External Services for MemoryOS Development
==============================================
Sub-issue #5.3: Create mock external services

This module provides mock implementations of external services for local development.
"""

import asyncio
import logging
import random
import time
from datetime import datetime, timedelta
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, HTTPException, Request

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app for mock services
app = FastAPI(
    title="MemoryOS Mock Services",
    description="Mock external services for local development",
    version="1.0.0",
)

# Mock data storage
mock_data = {
    "users": {},
    "tokens": {},
    "external_data": {},
    "webhooks": [],
    "notifications": [],
}

# ============================================================================
# Mock Identity Provider (OAuth2/OIDC)
# ============================================================================


@app.post("/oauth/token")
async def mock_oauth_token(request: Request):
    """Mock OAuth2 token endpoint."""
    form_data = await request.form()

    grant_type = form_data.get("grant_type")
    if grant_type == "client_credentials":
        # Mock agent authentication
        token = {
            "access_token": f"mock_agent_token_{uuid4().hex[:16]}",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "memory:read memory:write sync:access",
        }
    elif grant_type == "authorization_code":
        # Mock user authentication
        token = {
            "access_token": f"mock_user_token_{uuid4().hex[:16]}",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": f"mock_refresh_{uuid4().hex[:16]}",
            "scope": "memory:read profile:read",
        }
    else:
        raise HTTPException(status_code=400, detail="Unsupported grant type")

    # Store token for validation
    mock_data["tokens"][token["access_token"]] = {
        "token": token,
        "created_at": datetime.now(),
        "grant_type": grant_type,
    }

    logger.info(f"Issued mock token: {token['access_token'][:20]}...")
    return token


@app.get("/oauth/userinfo")
async def mock_userinfo(request: Request):
    """Mock OIDC userinfo endpoint."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = auth_header.split(" ")[1]
    token_data = mock_data["tokens"].get(token)

    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Mock user info
    userinfo = {
        "sub": f"user_{uuid4().hex[:12]}",
        "name": "Mock User",
        "email": "mock.user@example.com",
        "preferred_username": "mockuser",
        "groups": ["users", "memoryos_users"],
        "roles": ["user", "memory_user"],
    }

    return userinfo


# ============================================================================
# Mock External API Services
# ============================================================================


@app.get("/external/weather")
async def mock_weather_api():
    """Mock weather API for testing external integrations."""
    weather_data = {
        "location": "Mock City",
        "temperature": random.randint(-10, 35),
        "humidity": random.randint(30, 90),
        "description": random.choice(["sunny", "cloudy", "rainy", "snowy"]),
        "timestamp": datetime.now().isoformat(),
        "source": "mock_weather_service",
    }

    # Simulate occasional failures
    if random.random() < 0.1:
        raise HTTPException(
            status_code=503, detail="Weather service temporarily unavailable"
        )

    return weather_data


@app.get("/external/news")
async def mock_news_api(limit: int = 10):
    """Mock news API for testing content aggregation."""
    news_items = []

    for i in range(limit):
        article = {
            "id": f"article_{uuid4().hex[:8]}",
            "title": f"Mock News Article {i + 1}",
            "content": f"This is mock content for article {i + 1}. " * 10,
            "author": f"Mock Author {i + 1}",
            "published_at": (
                datetime.now() - timedelta(hours=random.randint(1, 72))
            ).isoformat(),
            "url": f"https://mock-news.example.com/article/{i + 1}",
            "category": random.choice(["tech", "science", "business", "health"]),
        }
        news_items.append(article)

    return {"articles": news_items, "total": limit}


@app.post("/external/translate")
async def mock_translation_api(request: Request):
    """Mock translation API for testing language processing."""
    data = await request.json()

    text = data.get("text", "")
    target_lang = data.get("target_lang", "en")
    source_lang = data.get("source_lang", "auto")

    # Mock translation (just prefix the text)
    translated_text = f"[TRANSLATED TO {target_lang.upper()}] {text}"

    result = {
        "translated_text": translated_text,
        "source_language": source_lang,
        "target_language": target_lang,
        "confidence": random.uniform(0.85, 0.99),
        "service": "mock_translator",
    }

    # Simulate processing delay
    await asyncio.sleep(random.uniform(0.1, 0.5))

    return result


# ============================================================================
# Mock Message Queue Services
# ============================================================================


@app.post("/queue/publish")
async def mock_queue_publish(request: Request):
    """Mock message queue publish endpoint."""
    data = await request.json()

    message = {
        "id": f"msg_{uuid4().hex[:12]}",
        "topic": data.get("topic", "default"),
        "payload": data.get("payload", {}),
        "timestamp": datetime.now().isoformat(),
        "status": "published",
    }

    # Store message
    if "messages" not in mock_data:
        mock_data["messages"] = []
    mock_data["messages"].append(message)

    logger.info(f"Published mock message: {message['id']} to topic: {message['topic']}")

    return {"message_id": message["id"], "status": "published"}


@app.get("/queue/consume/{topic}")
async def mock_queue_consume(topic: str, limit: int = 10):
    """Mock message queue consume endpoint."""
    if "messages" not in mock_data:
        return {"messages": []}

    # Filter messages by topic
    topic_messages = [msg for msg in mock_data["messages"] if msg["topic"] == topic]

    # Return latest messages
    recent_messages = topic_messages[-limit:] if topic_messages else []

    return {"messages": recent_messages, "topic": topic, "count": len(recent_messages)}


# ============================================================================
# Mock Webhook Services
# ============================================================================


@app.post("/webhooks/register")
async def mock_webhook_register(request: Request):
    """Mock webhook registration endpoint."""
    data = await request.json()

    webhook = {
        "id": f"webhook_{uuid4().hex[:8]}",
        "url": data.get("url"),
        "events": data.get("events", ["*"]),
        "secret": f"whsec_{uuid4().hex[:16]}",
        "created_at": datetime.now().isoformat(),
        "status": "active",
    }

    mock_data["webhooks"].append(webhook)

    logger.info(f"Registered mock webhook: {webhook['id']} -> {webhook['url']}")

    return webhook


@app.post("/webhooks/trigger/{webhook_id}")
async def mock_webhook_trigger(webhook_id: str, request: Request):
    """Mock webhook trigger for testing."""
    data = await request.json()

    # Find webhook
    webhook = next((w for w in mock_data["webhooks"] if w["id"] == webhook_id), None)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    # Create mock event
    event = {
        "id": f"evt_{uuid4().hex[:12]}",
        "type": data.get("event_type", "test.event"),
        "data": data.get("data", {}),
        "webhook_id": webhook_id,
        "timestamp": datetime.now().isoformat(),
    }

    logger.info(f"Triggered mock webhook: {webhook_id} with event: {event['type']}")

    return {"event": event, "status": "triggered"}


# ============================================================================
# Mock Storage Services
# ============================================================================


@app.post("/storage/upload")
async def mock_storage_upload(request: Request):
    """Mock file upload service."""
    # Simulate file upload processing
    await asyncio.sleep(random.uniform(0.2, 1.0))

    file_info = {
        "file_id": f"file_{uuid4().hex[:12]}",
        "filename": f"mock_file_{int(time.time())}.txt",
        "size": random.randint(1024, 10485760),  # 1KB to 10MB
        "content_type": "text/plain",
        "upload_url": f"https://mock-storage.example.com/files/file_{uuid4().hex[:12]}",
        "uploaded_at": datetime.now().isoformat(),
    }

    return file_info


@app.get("/storage/files/{file_id}")
async def mock_storage_download(file_id: str):
    """Mock file download service."""
    # Simulate file retrieval
    await asyncio.sleep(random.uniform(0.1, 0.3))

    file_info = {
        "file_id": file_id,
        "download_url": f"https://mock-storage.example.com/download/{file_id}",
        "expires_at": (datetime.now() + timedelta(hours=1)).isoformat(),
        "size": random.randint(1024, 10485760),
    }

    return file_info


# ============================================================================
# Mock Notification Services
# ============================================================================


@app.post("/notifications/send")
async def mock_notification_send(request: Request):
    """Mock notification service."""
    data = await request.json()

    notification = {
        "id": f"notif_{uuid4().hex[:8]}",
        "recipient": data.get("recipient"),
        "channel": data.get("channel", "email"),
        "subject": data.get("subject"),
        "message": data.get("message"),
        "status": "sent",
        "sent_at": datetime.now().isoformat(),
    }

    mock_data["notifications"].append(notification)

    logger.info(
        f"Sent mock notification: {notification['id']} via {notification['channel']}"
    )

    return notification


# ============================================================================
# Mock Service Health and Info
# ============================================================================


@app.get("/health")
async def mock_services_health():
    """Health check for mock services."""
    return {
        "status": "healthy",
        "services": {
            "oauth": "running",
            "external_apis": "running",
            "message_queue": "running",
            "webhooks": "running",
            "storage": "running",
            "notifications": "running",
        },
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": random.randint(3600, 86400),
    }


@app.get("/mock/stats")
async def mock_services_stats():
    """Statistics for mock services."""
    return {
        "tokens_issued": len(mock_data["tokens"]),
        "webhooks_registered": len(mock_data["webhooks"]),
        "messages_published": len(mock_data.get("messages", [])),
        "notifications_sent": len(mock_data["notifications"]),
        "active_since": datetime.now().isoformat(),
    }


@app.get("/mock/data")
async def mock_services_data():
    """Get all mock data (for debugging)."""
    return mock_data


@app.delete("/mock/reset")
async def mock_services_reset():
    """Reset all mock data."""
    global mock_data
    mock_data = {
        "users": {},
        "tokens": {},
        "external_data": {},
        "webhooks": [],
        "notifications": [],
    }

    logger.info("Reset all mock service data")
    return {"status": "reset", "timestamp": datetime.now().isoformat()}


# ============================================================================
# Main execution
# ============================================================================

if __name__ == "__main__":
    logger.info("🎭 Starting MemoryOS Mock Services")
    logger.info("==================================")
    logger.info("Available endpoints:")
    logger.info("  - OAuth2/OIDC: /oauth/token, /oauth/userinfo")
    logger.info(
        "  - External APIs: /external/weather, /external/news, /external/translate"
    )
    logger.info("  - Message Queue: /queue/publish, /queue/consume/{topic}")
    logger.info("  - Webhooks: /webhooks/register, /webhooks/trigger/{id}")
    logger.info("  - Storage: /storage/upload, /storage/files/{id}")
    logger.info("  - Notifications: /notifications/send")
    logger.info("  - Health: /health, /mock/stats, /mock/data")
    logger.info("")

    uvicorn.run(app, host="0.0.0.0", port=8090, log_level="info", reload=False)
