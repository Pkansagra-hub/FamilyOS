---
description: Adding new modules to existing services following architectural patterns.
applyTo: "**/*.py"
---
# 🧩 New Module Development

## 0) Module Purpose
- **Single responsibility** - one clear purpose per module
- **Clear interface** - well-defined inputs/outputs
- **Testable isolation** - can be tested independently

## 1) Module Structure
```
existing-service/
├── modules/
│   └── new-module/
│       ├── __init__.py
│       ├── module.py      # Core module logic
│       ├── models.py      # Module-specific models
│       ├── handlers.py    # Event/request handlers
│       └── tests/         # Module tests
```

## 2) Integration Patterns
- **Service registration** - register with parent service
- **Event subscription** - listen to relevant events
- **Storage extension** - extend existing store if needed
- **Policy integration** - enforce access controls

## 3) Implementation Standards
- Inherit from service base classes
- Use service-wide configuration
- Follow observability patterns
- Implement graceful shutdown

## 4) Testing Requirements
- Unit tests for module logic
- Integration tests with parent service
- Contract compliance validation
- Performance impact assessment

## 5) Documentation
- Module README with purpose/usage
- API documentation updates
- Integration guide for other developers