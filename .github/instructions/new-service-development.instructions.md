------

description: Creating new services following contracts-first methodology and MemoryOS architecture standards.description: Creating new services following contracts-first methodology and MemoryOS architecture standards.

applyTo: "**/*.py,**/README.md"applyTo: "**/*.py,**/README.md"

------

# 🏗️ New Service Development# 🏗️ New Service Development



## 0) Contracts First (Automated Tools Available)## 0) Contracts First

- **Define contracts** before any implementation using automation tools- **Define contracts** before any implementation.

- **API**: `contracts/api/openapi/modules/[service]-openapi.yaml`- **API**: OpenAPI spec in `contracts/api/openapi/modules/[service]-openapi.yaml`

- **Events**: `contracts/events/modules/[service]-catalog.json`- **Events**: Catalog + schemas in `contracts/events/modules/[service]-catalog.json`

- **Storage**: `contracts/storage/schemas/[service]-*.schema.json`- **Storage**: Schemas in `contracts/storage/schemas/[service]-*.schema.json`

- **Generate with**: `python contracts/automation/interactive_contract_builder.py`

## 1) Service Structure

## 1) Service Structure (Exact Layout)```

```[service-name]/

[service-name]/├── __init__.py           # Module exports

├── __init__.py           # Exports: [ServiceName]Service, [ServiceName]Store├── README.md            # Service documentation

├── README.md            # Service documentation with concrete examples├── service.py           # Main service class

├── service.py           # Main [ServiceName]Service class extending BaseService├── models.py            # Data models

├── models.py            # Pydantic models with contract validation├── store.py             # Storage interface (if needed)

├── store.py             # [ServiceName]Store(BaseStore) for persistence└── tests/               # Service tests

├── handlers.py          # Event handlers (async def handle_[event])```

└── tests/               # Test modules mirroring structure

    ├── test_service.py  # Service logic tests (≥95% coverage)## 2) Implementation Patterns

    ├── test_store.py    # Storage operation tests- **BaseStore** extension for storage services

    ├── test_handlers.py # Event handling tests- **EventBus** integration for event processing

    └── test_integration.py # Cross-component integration tests- **PolicyService** integration for access control

```- **Observability** instrumentation (metrics/traces/logs)



## 2) Implementation Patterns (Concrete Classes)## 3) Integration Requirements

- **BaseStore Extension**: Inherit from `storage.base_store.BaseStore`- **Policy enforcement** before operations

  ```python- **MLS group** integration for space-scoped data

  class [ServiceName]Store(BaseStore):- **UnitOfWork** pattern for transactional operations

      def __init__(self, db_path: str):- **Contract validation** in tests

          super().__init__(db_path)

          self.table_name = "[service]_data"## 4) Quality Gates

  ```- Unit tests ≥95% coverage

- **EventBus Integration**: Use `events.bus.EventBus` for async communication- Integration tests for all I/O

  ```python- Contract compliance validation

  async def handle_memory_created(self, event: MemoryCreatedEvent):- Performance benchmarks meet SLA

      # Process event with proper error handling- Security audit passed

  ```

- **PolicyService Integration**: Enforce RBAC/ABAC with `policy.service.PolicyService`## 5) VS Code Workflow

  ```python```bash

  await self.policy.check_permission(actor, "read", resource, context)# Use Tasks:

  ```# 1. "Plan New Service" - Requirements gathering

- **Observability**: Instrument with `observability.{metrics,trace,logging}`# 2. "Scaffold New Service" - Generate structure

  ```python# 3. "Validate Contracts" - Check compliance

  with trace.start_span(f"{service_name}.{method_name}") as span:# 4. "Run Service Tests" - Execute test suite

      metrics.increment(f"familyos_{service_name}_operations_total")```
  ```

## 3) Integration Requirements (Specific Components)
- **Policy Enforcement**: Every operation must call `PolicyService.check_permission()`
- **MLS Group Integration**: Use `security.mls.MLSGroup` for space-scoped encryption
- **UnitOfWork Pattern**: Wrap transactions with `storage.unit_of_work.UnitOfWork`
- **Contract Validation**: All I/O must validate against contract schemas

## 4) Quality Gates (Measurable Criteria)
- **Unit Tests**: ≥95% coverage measured with `coverage.py`
- **Integration Tests**: All I/O paths tested with real components
- **Contract Compliance**: 100% schema validation with `python contracts/automation/validation_helper.py`
- **Performance**: Meet SLA requirements (default: <200ms p95, >1000 req/s)
- **Security Audit**: Pass `python scripts/security/audit_service.py [service-name]`

## 5) Brain Region Mapping (For Cognitive Services)
- **Hippocampus**: Memory formation, consolidation, retrieval patterns
- **Cortex**: Higher-order processing, decision making, executive functions
- **Cerebellum**: Motor control, procedural learning, coordination
- **Amygdala**: Emotional processing, threat detection, fear conditioning
- **Thalamus**: Sensory relay, attention gating, consciousness
- **Brainstem**: Basic functions, arousal, autonomic control

## 6) VS Code Workflow (Automated Tasks)
```bash
# Use VS Code Tasks (Ctrl+Shift+P → "Tasks: Run Task"):
# 1. "workflow:new-service-plan" - Requirements gathering with templates
# 2. "service:scaffold-new" - Generate directory structure
# 3. "service:create-contracts" - Create contract templates
# 4. "contracts:validate" - Validate contract compliance
# 5. "tests:ward" - Run WARD test suite
# 6. "ci:fast" - Quick validation (lint, type, test)
```

## 7) Implementation Checklist
- [ ] Contracts created and validated with automation tools
- [ ] Service class implements required methods with type hints
- [ ] Store class extends BaseStore with proper table schema
- [ ] Event handlers registered with EventBus
- [ ] Policy enforcement implemented at all entry points
- [ ] Observability instrumentation added (metrics/traces/logs)
- [ ] Test suite achieving ≥95% coverage with WARD
- [ ] Integration tests with real components (no mocks)
- [ ] Performance benchmarks meeting SLA requirements
- [ ] Security audit passing all checks
- [ ] Documentation complete with API examples

## 8) Service Generation Commands
```bash
# Generate service contracts
python contracts/automation/interactive_contract_builder.py
# Follow prompts for service type, brain region, and requirements

# Generate service scaffold
python scripts/service/scaffold_service.py [service-name] --brain-region [region]

# Validate implementation
python contracts/automation/validation_helper.py --service [service-name]
python -m ward test --path [service-name]/tests/
python scripts/security/audit_service.py [service-name]
```

## 9) Error Prevention Guidelines
- **No Simulation Code**: Never use `asyncio.sleep()` or `time.sleep()` in production
- **Real Components**: Use actual storage, events, and policy services in tests
- **Contract Validation**: Always validate I/O against schemas before processing
- **Error Handling**: Implement proper exception handling with specific error types
- **Resource Cleanup**: Use context managers and proper async cleanup patterns
