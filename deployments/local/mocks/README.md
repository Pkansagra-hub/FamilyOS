# Mock External Services

This directory contains mock implementations of external services for MemoryOS development and testing.

## Overview

The mock services provide a complete simulation of external dependencies, allowing developers to work without requiring real external service connections. This enables:

- **Isolated Development**: Work without internet connectivity or external service accounts
- **Predictable Testing**: Consistent, controllable responses for automated tests
- **Cost Reduction**: No charges from external APIs during development
- **Enhanced Security**: No real credentials or data exposure during development

## Services Included

### 🔐 Identity Provider (OAuth2/OIDC)
- **Endpoints**: `/oauth/token`, `/oauth/userinfo`
- **Features**: Mock user authentication, JWT token simulation, role-based access
- **Use Cases**: Testing authentication flows, user session management

### 🌐 External API Services
- **Weather API**: `/external/weather` - Mock weather data with simulated failures
- **News API**: `/external/news` - Generated news articles with various categories
- **Translation API**: `/external/translate` - Mock translation service with confidence scores

### 📨 Message Queue Services
- **Publish**: `/queue/publish` - Message publishing simulation
- **Consume**: `/queue/consume/{topic}` - Topic-based message consumption
- **Features**: Topic filtering, message persistence, consumption tracking

### 🔗 Webhook Services
- **Registration**: `/webhooks/register` - Webhook endpoint registration
- **Triggering**: `/webhooks/trigger/{id}` - Manual webhook event triggering
- **Features**: Event filtering, secret validation, delivery simulation

### 💾 Storage Services
- **Upload**: `/storage/upload` - File upload simulation with metadata
- **Download**: `/storage/files/{id}` - File retrieval with signed URLs
- **Features**: File size simulation, content type detection, expiry handling

### 📢 Notification Services
- **Send**: `/notifications/send` - Multi-channel notification delivery
- **Channels**: Email, SMS, Push, Webhook notifications
- **Features**: Template support, delivery tracking, channel fallback

## Quick Start

### Local Development

1. **Install Dependencies**:
   ```bash
   pip install -r requirements-mock.txt
   ```

2. **Run Mock Services**:
   ```bash
   python mock_services.py
   ```

3. **Access Services**:
   - API Documentation: http://localhost:8090/docs
   - Health Check: http://localhost:8090/health
   - Service Stats: http://localhost:8090/mock/stats

### Kubernetes Deployment

1. **Build Docker Image**:
   ```bash
   docker build -t memoryos/mock-services:dev .
   ```

2. **Deploy to Kubernetes**:
   ```bash
   kubectl apply -f ../k8s/mock-services-deployment.yaml
   ```

3. **Port Forward for Access**:
   ```bash
   kubectl port-forward -n memoryos-dev svc/mock-services 8090:8090
   ```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MOCK_HOST` | `0.0.0.0` | Service bind address |
| `MOCK_PORT` | `8090` | Service port |
| `LOG_LEVEL` | `info` | Logging level |
| `OAUTH_CLIENT_ID` | `memoryos_dev` | OAuth client identifier |
| `OAUTH_CLIENT_SECRET` | `dev_secret_key` | OAuth client secret |
| `TOKEN_EXPIRY_SECONDS` | `3600` | Token validity duration |
| `WEATHER_FAILURE_RATE` | `0.1` | Weather API failure rate (0.0-1.0) |
| `MAX_MESSAGES_PER_TOPIC` | `1000` | Message queue capacity per topic |
| `MAX_FILE_SIZE_MB` | `100` | Maximum simulated file size |

### Configuration File

The `config.py` file contains detailed configuration options for all mock services. Key settings include:

```python
# Service behavior
weather_api_failure_rate: float = 0.1  # 10% failure rate
news_api_delay_range: tuple = (0.1, 0.5)  # Response delay range

# Resource limits
max_messages_per_topic: int = 1000
max_file_size_mb: int = 100
max_webhooks: int = 100
```

## API Examples

### OAuth Authentication

```bash
# Get access token
curl -X POST http://localhost:8090/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=memoryos_dev"

# Get user info
curl -X GET http://localhost:8090/oauth/userinfo \
  -H "Authorization: Bearer <access_token>"
```

### External APIs

```bash
# Get weather data
curl http://localhost:8090/external/weather

# Get news articles
curl http://localhost:8090/external/news?limit=5

# Translate text
curl -X POST http://localhost:8090/external/translate \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "target_lang": "es"}'
```

### Message Queue

```bash
# Publish message
curl -X POST http://localhost:8090/queue/publish \
  -H "Content-Type: application/json" \
  -d '{"topic": "memory_updates", "payload": {"user_id": "123", "action": "create"}}'

# Consume messages
curl http://localhost:8090/queue/consume/memory_updates?limit=10
```

### Webhooks

```bash
# Register webhook
curl -X POST http://localhost:8090/webhooks/register \
  -H "Content-Type: application/json" \
  -d '{"url": "http://localhost:8080/webhook", "events": ["memory.created", "memory.updated"]}'

# Trigger webhook
curl -X POST http://localhost:8090/webhooks/trigger/webhook_12345 \
  -H "Content-Type: application/json" \
  -d '{"event_type": "memory.created", "data": {"memory_id": "mem_123"}}'
```

## Monitoring and Debugging

### Health Checks

```bash
# Service health
curl http://localhost:8090/health

# Service statistics
curl http://localhost:8090/mock/stats

# View all mock data
curl http://localhost:8090/mock/data
```

### Reset Mock Data

```bash
# Clear all stored mock data
curl -X DELETE http://localhost:8090/mock/reset
```

## Integration with MemoryOS

### Service Discovery

The mock services are automatically discoverable within the Kubernetes cluster:

```yaml
# In MemoryOS configuration
external_services:
  oauth_provider: "http://mock-services.memoryos-dev.svc.cluster.local:8090"
  weather_api: "http://mock-services.memoryos-dev.svc.cluster.local:8090/external/weather"
  translation_api: "http://mock-services.memoryos-dev.svc.cluster.local:8090/external/translate"
```

### Development Configuration

Update your MemoryOS development configuration to use mock services:

```python
# config/development.py
EXTERNAL_SERVICES = {
    'oauth': {
        'provider_url': 'http://localhost:8090',
        'client_id': 'memoryos_dev',
        'client_secret': 'dev_secret_key'
    },
    'apis': {
        'weather': 'http://localhost:8090/external/weather',
        'news': 'http://localhost:8090/external/news',
        'translation': 'http://localhost:8090/external/translate'
    }
}
```

## Testing Scenarios

### Failure Simulation

The mock services include built-in failure scenarios:

- **Weather API**: 10% random failure rate (configurable)
- **Network Delays**: Configurable response delays
- **Resource Limits**: Maximum file sizes, message counts, webhook limits

### Data Scenarios

Pre-configured test data includes:

- **User Profiles**: Developer, Tester, Admin roles
- **News Categories**: Technology, Science, Business, etc.
- **Weather Conditions**: Various weather patterns with realistic data
- **Notification Templates**: Welcome, Updates, Alerts, Summaries

## Troubleshooting

### Common Issues

1. **Service Not Starting**: Check port availability and dependencies
2. **Authentication Failures**: Verify client credentials and token format
3. **API Timeouts**: Adjust delay ranges in configuration
4. **Resource Limits**: Check message/webhook/file limits

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
LOG_LEVEL=debug python mock_services.py
```

### Logs and Monitoring

- Service logs include request/response details
- Health endpoint provides service status
- Stats endpoint shows usage metrics
- Prometheus metrics available at `/metrics` (if enabled)

## Development

### Adding New Mock Services

1. Add endpoint handlers to `mock_services.py`
2. Update configuration in `config.py`
3. Add documentation to this README
4. Include integration examples

### Testing Mock Services

```bash
# Run tests (if test suite exists)
python -m ward test --path tests/

# Manual API testing
curl -X GET http://localhost:8090/docs
```

---

This mock service setup provides a complete, isolated development environment for MemoryOS, enabling efficient development and testing without external dependencies.
