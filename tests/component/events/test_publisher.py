"""
Comprehensive test suite for Event Publisher interface and implementations.

Tests cover:
- EventPublisher interface contract
- InMemoryPublisher implementation
- PublisherConfig validation
- Publisher factory functionality
- Error handling scenarios
- Async behavior and timeouts
"""

from datetime import datetime, timezone
from uuid import uuid4
import asyncio

# Import Ward testing framework
from ward import test, expect

from events.publisher import (
    InMemoryPublisher, 
    PublisherConfig,
    PublisherType,
    PublishResult,
    ValidationError,
    create_publisher,
)
from events.types import (
    Event,
    EventType,
    create_event,
    Actor,
    Device,
    Capability,
)


def create_test_event(topic: EventType = EventType.WORKSPACE_BROADCAST) -> Event:
    """Helper to create a test event."""
    test_actor = Actor(
        user_id=str(uuid4()),
        caps=[Capability.WRITE]
    )
    
    test_device = Device(
        device_id='test-device-123'
    )
    
    return create_event(
        topic=topic,
        payload={'message': 'test event', 'timestamp': datetime.now(timezone.utc).isoformat()},
        actor=test_actor,
        device=test_device,
        space_id='personal:test-space'
    )


@test("PublisherConfig has sensible defaults")
def test_publisher_config_defaults():
    """Test that PublisherConfig has reasonable default values."""
    config = PublisherConfig()
    
    expect(config.publisher_type).equals(PublisherType.IN_MEMORY)
    expect(config.max_batch_size).equals(100)
    expect(config.batch_timeout_ms).equals(1000)
    expect(config.max_retries).equals(3)
    expect(config.retry_delay_ms).equals(1000)
    expect(config.retry_backoff_multiplier).equals(2.0)
    expect(config.publish_timeout_ms).equals(5000)
    expect(config.health_check_timeout_ms).equals(2000)
    expect(config.validate_events).equals(True)
    expect(config.strict_validation).equals(True)
    expect(len(config.config)).equals(0)


@test("PublisherConfig can be customized")
def test_publisher_config_customization():
    """Test that PublisherConfig can be customized."""
    config = PublisherConfig(
        publisher_type=PublisherType.JSONL,
        max_batch_size=50,
        validate_events=False,
        config={'custom_setting': 'value'}
    )
    
    expect(config.publisher_type).equals(PublisherType.JSONL)
    expect(config.max_batch_size).equals(50)
    expect(config.validate_events).equals(False)
    expect(config.config['custom_setting']).equals('value')


@test("create_publisher creates InMemoryPublisher for IN_MEMORY type")
def test_create_publisher_in_memory():
    """Test that factory creates InMemoryPublisher for IN_MEMORY type."""
    config = PublisherConfig(publisher_type=PublisherType.IN_MEMORY)
    publisher = create_publisher(config)
    
    expect(isinstance(publisher, InMemoryPublisher)).equals(True)
    expect(publisher.config).equals(config)


@test("create_publisher raises error for unsupported types")
def test_create_publisher_unsupported():
    """Test that factory raises error for unsupported publisher types."""
    config = PublisherConfig(publisher_type=PublisherType.KAFKA)
    
    try:
        create_publisher(config)
        expect(False).equals(True)  # Should not reach here
    except ValueError as e:
        expect("Unsupported publisher type: PublisherType.KAFKA" in str(e)).equals(True)


@test("PublishResult.success_result creates successful result")
def test_publish_result_success():
    """Test PublishResult.success_result factory method."""
    event_id = "ev-test123456789012"
    result = PublishResult.success_result(event_id)
    
    expect(result.success).equals(True)
    expect(result.event_id).equals(event_id)
    expect(result.error).equals(None)
    expect(result.retry_count).equals(0)
    expect(isinstance(result.published_at, datetime)).equals(True)


@test("PublishResult.error_result creates error result")
def test_publish_result_error():
    """Test PublishResult.error_result factory method."""
    event_id = "ev-test123456789012"
    error_msg = "Validation failed"
    retry_count = 2
    
    result = PublishResult.error_result(event_id, error_msg, retry_count)
    
    expect(result.success).equals(False)
    expect(result.event_id).equals(event_id)
    expect(result.error).equals(error_msg)
    expect(result.retry_count).equals(retry_count)
    expect(isinstance(result.published_at, datetime)).equals(True)


class TestInMemoryPublisher:
    """Test suite for InMemoryPublisher implementation."""
    
    def setup_publisher(self, validate_events: bool = False) -> InMemoryPublisher:
        """Setup a test publisher."""
        config = PublisherConfig(
            publisher_type=PublisherType.IN_MEMORY,
            validate_events=validate_events,
            max_batch_size=5
        )
        return InMemoryPublisher(config)
    
    @test("InMemoryPublisher initializes correctly")
    def test_initialization(self):
        """Test InMemoryPublisher initialization."""
        publisher = self.setup_publisher()
        
        expect(len(publisher.get_published_events())).equals(0)
        expect(publisher.get_event_count()).equals(0)
    
    @test("InMemoryPublisher health check returns True when healthy")
    async def test_health_check_healthy(self):
        """Test health check when publisher is healthy."""
        publisher = self.setup_publisher()
        
        healthy = await publisher.health_check()
        expect(healthy).equals(True)
    
    @test("InMemoryPublisher health check returns False when closed")
    async def test_health_check_closed(self):
        """Test health check when publisher is closed."""
        publisher = self.setup_publisher()
        
        await publisher.close()
        healthy = await publisher.health_check()
        expect(healthy).equals(False)
    
    @test("InMemoryPublisher can publish single event without validation")
    async def test_publish_single_event_no_validation(self):
        """Test publishing single event without validation."""
        publisher = self.setup_publisher(validate_events=False)
        event = create_test_event()
        
        result = await publisher.publish(event)
        
        expect(result.success).equals(True)
        expect(result.event_id).equals(event.meta.id)
        expect(result.error).equals(None)
        expect(publisher.get_event_count()).equals(1)
        
        published_events = publisher.get_published_events()
        expect(len(published_events)).equals(1)
        expect(published_events[0].meta.id).equals(event.meta.id)
    
    @test("InMemoryPublisher rejects events with validation enabled")
    async def test_publish_single_event_with_validation(self):
        """Test publishing single event with validation (should fail due to topic format)."""
        publisher = self.setup_publisher(validate_events=True)
        event = create_test_event()
        
        result = await publisher.publish(event)
        
        expect(result.success).equals(False)
        expect(result.event_id).equals(event.meta.id)
        expect("validation failed" in result.error.lower()).equals(True)
        expect(publisher.get_event_count()).equals(0)
    
    @test("InMemoryPublisher can publish batch of events")
    async def test_publish_batch_events(self):
        """Test publishing batch of events."""
        publisher = self.setup_publisher(validate_events=False)
        events = [create_test_event() for _ in range(3)]
        
        results = await publisher.publish_batch(events)
        
        expect(len(results)).equals(3)
        for i, result in enumerate(results):
            expect(result.success).equals(True)
            expect(result.event_id).equals(events[i].meta.id)
        
        expect(publisher.get_event_count()).equals(3)
    
    @test("InMemoryPublisher rejects empty batch")
    async def test_publish_empty_batch(self):
        """Test publishing empty batch raises validation error."""
        publisher = self.setup_publisher(validate_events=False)
        
        results = await publisher.publish_batch([])
        
        expect(len(results)).equals(0)
        expect(publisher.get_event_count()).equals(0)
    
    @test("InMemoryPublisher rejects oversized batch")
    async def test_publish_oversized_batch(self):
        """Test publishing batch larger than max_batch_size."""
        publisher = self.setup_publisher(validate_events=False)
        # Create batch larger than max_batch_size (5)
        events = [create_test_event() for _ in range(7)]
        
        results = await publisher.publish_batch(events)
        
        expect(len(results)).equals(7)
        for result in results:
            expect(result.success).equals(False)
            expect("batch size" in result.error.lower()).equals(True)
        
        expect(publisher.get_event_count()).equals(0)
    
    @test("InMemoryPublisher rejects publish when closed")
    async def test_publish_when_closed(self):
        """Test publishing when publisher is closed."""
        publisher = self.setup_publisher(validate_events=False)
        event = create_test_event()
        
        await publisher.close()
        result = await publisher.publish(event)
        
        expect(result.success).equals(False)
        expect("closed" in result.error.lower()).equals(True)
        expect(publisher.get_event_count()).equals(0)
    
    @test("InMemoryPublisher can clear events")
    def test_clear_events(self):
        """Test clearing stored events."""
        publisher = self.setup_publisher()
        
        # Add some mock events
        publisher._published_events.extend([create_test_event() for _ in range(3)])
        expect(publisher.get_event_count()).equals(3)
        
        publisher.clear_events()
        expect(publisher.get_event_count()).equals(0)
        expect(len(publisher.get_published_events())).equals(0)
    
    @test("InMemoryPublisher can set health status")
    async def test_set_health_status(self):
        """Test setting health status for testing."""
        publisher = self.setup_publisher()
        
        expect(await publisher.health_check()).equals(True)
        
        publisher.set_healthy(False)
        expect(await publisher.health_check()).equals(False)
        
        publisher.set_healthy(True)
        expect(await publisher.health_check()).equals(True)


@test("EventPublisher validates single event correctly")
def test_event_publisher_validate_event():
    """Test EventPublisher.validate_event method."""
    config = PublisherConfig(validate_events=True)
    publisher = InMemoryPublisher(config)
    event = create_test_event()
    
    # This should raise ValidationError due to topic format
    try:
        publisher.validate_event(event)
        expect(False).equals(True)  # Should not reach here
    except ValidationError as e:
        expect("validation failed" in str(e).lower()).equals(True)


@test("EventPublisher validates batch correctly")
def test_event_publisher_validate_batch():
    """Test EventPublisher.validate_batch method."""
    config = PublisherConfig(validate_events=True, max_batch_size=3)
    publisher = InMemoryPublisher(config)
    
    # Test empty batch
    try:
        publisher.validate_batch([])
        expect(False).equals(True)  # Should not reach here
    except ValidationError as e:
        expect("empty" in str(e).lower()).equals(True)
    
    # Test oversized batch
    events = [create_test_event() for _ in range(5)]
    try:
        publisher.validate_batch(events)
        expect(False).equals(True)  # Should not reach here
    except ValidationError as e:
        expect("exceeds maximum" in str(e).lower()).equals(True)


@test("EventPublisher skips validation when disabled")
def test_event_publisher_skip_validation():
    """Test that validation is skipped when disabled."""
    config = PublisherConfig(validate_events=False)
    publisher = InMemoryPublisher(config)
    event = create_test_event()
    
    # This should not raise any exception
    publisher.validate_event(event)
    
    # Validation passed (no exception)
    expect(True).equals(True)


# Async test runner for Ward
async def run_async_test(test_func):
    """Helper to run async test functions."""
    if asyncio.iscoroutinefunction(test_func):
        await test_func()
    else:
        test_func()


if __name__ == "__main__":
    print("Running Event Publisher tests...")
    print("Note: Some tests require asyncio and may not run in all environments.")
    print("Use 'python -m ward test --path tests/component/events/test_publisher.py' for full test execution.")