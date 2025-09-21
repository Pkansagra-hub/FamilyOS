---
description: Python development standards for FamilyOS/MemoryOS.
applyTo: "**/*.py"
---
# 🐍 Python Development — Project Standards

> Target: Python 3.11 • Tooling: Poetry, ruff, black, mypy(strict), ward

## 1) Style & Tooling (Exact Commands)
- **Formatting**: `python -m black .` (default profile). No manual line wraps.
- **Import Sorting**: `python -m ruff check --select I .` for import organization
- **Linting**: `python -m ruff check .` (E, F, I, B, UP, NPY, PLC rules enabled)
- **Type Checking**: `python -m mypy --strict .` must pass for all touched code
- **Line Length**: Target **100** characters (configured in pyproject.toml)
- **Dependencies**: Use `poetry add [package]` for all new dependencies

## 2) Code Structure (Concrete Patterns)
- **Single Purpose Modules**: Each .py file has one clear responsibility
- **No Global State**: Use dependency injection via constructors
  ```python
  class MemoryService:
      def __init__(self, store: MemoryStore, policy: PolicyService):
          self.store = store
          self.policy = policy
  ```
- **Data Models**: Use `dataclasses` for internal data, `pydantic.BaseModel` for I/O
  ```python
  from pydantic import BaseModel

  class MemoryRequest(BaseModel):
      content: str
      user_id: str
      space_id: str
  ```
- **Error Handling**: Raise specific exceptions, handle at appropriate boundaries
  ```python
  class MemoryNotFoundError(Exception):
      def __init__(self, memory_id: str):
          super().__init__(f"Memory {memory_id} not found")
  ```

## 3) Security & Privacy (Mandatory Enforcement)
- **Never Log PII**: Use structured logging with redaction
  ```python
  from observability.logging import get_logger

  logger = get_logger(__name__)
  logger.info("Memory created", extra={"memory_id": memory_id, "user_id": "[REDACTED]"})
  ```
- **Band Enforcement**: Respect GREEN/AMBER/RED/BLACK data classification
- **Policy Validation**: Check permissions before operations
  ```python
  await self.policy.check_permission(actor, "read", memory, context)
  ```
- **Data Redaction**: Use `policy.redactor.RedactionService` for sensitive data

## 4) Observability (Required Instrumentation)
- **Metrics**: Prometheus format with `familyos_` prefix
  ```python
  from observability.metrics import counter, histogram

  request_count = counter("familyos_memory_requests_total", ["method", "status"])
  response_time = histogram("familyos_memory_response_seconds", ["endpoint"])
  ```
- **Traces**: Use context managers for spans
  ```python
  from observability.trace import start_span

  async def create_memory(self, request: MemoryRequest):
      with start_span("memory_service.create_memory") as span:
          span.set_attribute("user_id", request.user_id)
          # Implementation here
  ```
- **Structured Logs**: JSON format with correlation IDs
  ```python
  logger.info("Memory operation completed", extra={
      "operation": "create",
      "memory_id": memory_id,
      "correlation_id": context.correlation_id,
      "duration_ms": duration
  })
  ```

## 5) Async Programming (Production Patterns)
- **No Blocking Calls**: Use async/await for I/O operations
- **Thread Pool**: Use `asyncio.get_event_loop().run_in_executor()` for CPU-bound work
- **Resource Management**: Use async context managers
  ```python
  async with self.db.transaction() as tx:
      await tx.execute("INSERT INTO memories ...")
      await tx.commit()
  ```
- **Error Handling**: Proper exception handling in async contexts
  ```python
  try:
      result = await async_operation()
  except SpecificError as e:
      logger.error("Operation failed", extra={"error": str(e)})
      raise ServiceError("Failed to complete operation") from e
  ```

## 6) Testing Integration (WARD Framework)
```python
from ward import test, fixture
import asyncio

@fixture
async def memory_service():
    # Setup real components for testing
    store = MemoryStore(":memory:")
    policy = PolicyService()
    return MemoryService(store, policy)

@test("memory service creates memory correctly")
async def test_memory_creation(memory_service=memory_service):
    request = MemoryRequest(content="test", user_id="123", space_id="456")
    memory = await memory_service.create_memory(request)
    assert memory.content == "test"
    assert memory.user_id == "123"
```

## 7) Contract Integration (Schema Validation)
```python
from contracts.validation import validate_schema

class MemoryService:
    async def create_memory(self, request: dict) -> dict:
        # Validate input against contract
        validate_schema(request, "contracts/api/openapi/modules/memory-openapi.yaml#/components/schemas/MemoryRequest")

        # Process request
        result = await self._create_memory_internal(request)

        # Validate output against contract
        validate_schema(result, "contracts/api/openapi/modules/memory-openapi.yaml#/components/schemas/Memory")
        return result
```

## 8) Performance Guidelines
- **Batch Operations**: Process multiple items together when possible
- **Connection Pooling**: Reuse database connections, HTTP clients
- **Caching**: Use appropriate caching strategies with TTL
- **Pagination**: Implement pagination for large result sets
- **Monitoring**: Track performance metrics and set alerts

## 9) Common Pitfalls (Strict Enforcement)
- ✅ **Do**: Validate inputs with Pydantic models at service boundaries
- ✅ **Do**: Check policy permissions before state changes
- ✅ **Do**: Use type hints on all function signatures
- ✅ **Do**: Handle exceptions specifically, not with bare `except:`
- ❌ **Never**: Use `asyncio.sleep()` or `time.sleep()` for delays
- ❌ **Never**: Bypass redaction or log PII directly
- ❌ **Never**: Use global variables for state management
- ❌ **Never**: Import internal modules from other services

## 10) Development Workflow Commands
```bash
# Code quality checks (run before commit)
python -m black .
python -m ruff check . --fix
python -m mypy --strict .

# Testing with coverage
python -m ward test --path tests/
coverage run -m ward test --path tests/
coverage report --fail-under=95

# Contract validation
python contracts/automation/validation_helper.py --python-schemas

# Performance profiling
python -m cProfile -o profile.stats your_script.py
python -c "import pstats; pstats.Stats('profile.stats').sort_stats('tottime').print_stats(20)"
```
