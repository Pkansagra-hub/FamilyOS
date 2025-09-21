"""
Mock Services Configuration
==========================
Configuration and environment setup for mock external services.
"""

import os
from dataclasses import dataclass
from typing import List


@dataclass
class MockServiceConfig:
    """Configuration for mock services."""

    # Service settings
    host: str = "0.0.0.0"
    port: int = 8090
    reload: bool = True
    log_level: str = "info"

    # OAuth/OIDC settings
    oauth_issuer: str = "http://localhost:8090"
    oauth_client_id: str = "memoryos_dev"
    oauth_client_secret: str = "dev_secret_key"
    token_expiry_seconds: int = 3600

    # External API settings
    weather_api_failure_rate: float = 0.1  # 10% failure rate
    news_api_delay_range: tuple = (0.1, 0.5)  # seconds
    translation_api_delay_range: tuple = (0.1, 0.5)  # seconds

    # Message queue settings
    max_messages_per_topic: int = 1000
    message_retention_hours: int = 24

    # Storage settings
    max_file_size_mb: int = 100
    storage_base_url: str = "https://mock-storage.example.com"

    # Webhook settings
    webhook_timeout_seconds: int = 30
    max_webhooks: int = 100

    # Notification settings
    notification_channels: List[str] = None

    def __post_init__(self):
        """Set default values after initialization."""
        if self.notification_channels is None:
            self.notification_channels = ["email", "sms", "push", "webhook"]

    @classmethod
    def from_env(cls) -> "MockServiceConfig":
        """Create configuration from environment variables."""
        return cls(
            host=os.getenv("MOCK_HOST", "0.0.0.0"),
            port=int(os.getenv("MOCK_PORT", "8090")),
            reload=os.getenv("MOCK_RELOAD", "true").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "info").lower(),
            oauth_issuer=os.getenv("OAUTH_ISSUER", "http://localhost:8090"),
            oauth_client_id=os.getenv("OAUTH_CLIENT_ID", "memoryos_dev"),
            oauth_client_secret=os.getenv("OAUTH_CLIENT_SECRET", "dev_secret_key"),
            token_expiry_seconds=int(os.getenv("TOKEN_EXPIRY_SECONDS", "3600")),
            weather_api_failure_rate=float(os.getenv("WEATHER_FAILURE_RATE", "0.1")),
            max_messages_per_topic=int(os.getenv("MAX_MESSAGES_PER_TOPIC", "1000")),
            message_retention_hours=int(os.getenv("MESSAGE_RETENTION_HOURS", "24")),
            max_file_size_mb=int(os.getenv("MAX_FILE_SIZE_MB", "100")),
            storage_base_url=os.getenv(
                "STORAGE_BASE_URL", "https://mock-storage.example.com"
            ),
            webhook_timeout_seconds=int(os.getenv("WEBHOOK_TIMEOUT_SECONDS", "30")),
            max_webhooks=int(os.getenv("MAX_WEBHOOKS", "100")),
        )


# Mock data templates
MOCK_USER_PROFILES = [
    {
        "id": "user_001",
        "name": "Alice Developer",
        "email": "alice@memoryos.dev",
        "role": "developer",
        "groups": ["users", "developers", "memoryos_users"],
    },
    {
        "id": "user_002",
        "name": "Bob Tester",
        "email": "bob@memoryos.dev",
        "role": "tester",
        "groups": ["users", "testers", "memoryos_users"],
    },
    {
        "id": "user_003",
        "name": "Carol Admin",
        "email": "carol@memoryos.dev",
        "role": "admin",
        "groups": ["users", "admins", "memoryos_users", "memoryos_admins"],
    },
]

MOCK_NEWS_CATEGORIES = [
    "technology",
    "science",
    "business",
    "health",
    "sports",
    "entertainment",
    "politics",
    "environment",
    "education",
]

MOCK_WEATHER_CONDITIONS = [
    {"condition": "sunny", "temp_range": (15, 35)},
    {"condition": "cloudy", "temp_range": (5, 25)},
    {"condition": "rainy", "temp_range": (0, 20)},
    {"condition": "snowy", "temp_range": (-10, 5)},
    {"condition": "stormy", "temp_range": (5, 25)},
    {"condition": "foggy", "temp_range": (0, 15)},
]

MOCK_NOTIFICATION_TEMPLATES = {
    "welcome": {
        "subject": "Welcome to MemoryOS",
        "template": "Welcome {name}! Your MemoryOS account is ready.",
    },
    "memory_update": {
        "subject": "Memory Update",
        "template": "Your memory '{memory_title}' has been updated.",
    },
    "system_alert": {
        "subject": "System Alert",
        "template": "System alert: {alert_message}",
    },
    "weekly_summary": {
        "subject": "Weekly Memory Summary",
        "template": "Your weekly memory summary is ready. You have {memory_count} memories.",
    },
}

# Export configuration instance
config = MockServiceConfig.from_env()
