# UUID Generator Utility

The UUID generator utility provides secure and consistent UUID generation for various FamilyOS system components.

## Overview

Located in `api/utils/uuid_generator.py`, this utility offers:

- **User ID generation**: Secure UUIDs for user identification
- **Device ID generation**: UUIDs with optional prefixes for device identification
- **Session and Request IDs**: For API tracing and session management
- **Space IDs**: For space/context identification with type prefixes
- **Event IDs**: For event bus operations
- **Username to UUID mapping**: Deterministic UUID generation from usernames
- **Development helpers**: Consistent UUIDs for testing and development

## Key Features

### 🔒 Security
- Uses `uuid4()` for cryptographically secure random UUIDs
- Provides `secrets.token_hex()` for secure token generation
- Validates UUID formats and normalizes UUID strings

### 🧩 Integration Ready
- Compatible with SecurityContext schema (accepts both UUID and string formats)
- Supports development mode with consistent username-to-UUID mapping
- Designed for policy system integration and authentication middleware

### 🛠️ Development Support
- Deterministic UUID generation for consistent testing
- Development user context creation with all required identifiers
- UUID validation and normalization utilities

## Usage Examples

### Basic UUID Generation

```python
from api.utils import new_user_id, new_device_id, new_session_id

# Generate UUIDs for different purposes
user_id = new_user_id()                    # User identifier
device_id = new_device_id("laptop")        # Device with prefix
session_id = new_session_id()              # API session
space_id = new_space_id("family")          # Space with type
```

### Development Mode

```python
from api.utils import username_to_uuid, create_dev_user_context

# Convert username to consistent UUID (deterministic)
user_uuid = username_to_uuid("john_doe")   # Always same UUID for "john_doe"

# Create complete dev context
dev_context = create_dev_user_context("alice", "mobile")
# Returns: {
#   "user_id": "f7d8be13-2a72-5104-bd02-7a5964737a91",
#   "username": "alice",
#   "device_id": "mobile_681f39f1-1289-4ecd-b7ad-560e52cc6083",
#   "session_id": "fc6854a5-42f4-4fcd-a629-e30d649f6438",
#   "space_id": "personal:ab4d2a94-5c81-416b-9042-9f06a1d53ab1",
#   "created_at": "2025-09-14T15:57:48.436591+00:00"
# }
```

### Authentication Integration

```python
from api.utils import UUIDGenerator, is_uuid
from api.schemas import SecurityContext

# Handle both username and UUID formats
user_input = "john_doe"  # or "123e4567-e89b-12d3-a456-426614174000"

if is_uuid(user_input):
    user_id = user_input
else:
    # Convert username to deterministic UUID for consistency
    user_id = UUIDGenerator.generate_username_to_uuid_mapping(user_input)

# Create SecurityContext (now accepts string user_id)
context = SecurityContext(
    user_id=user_id,
    device_id=new_device_id("web"),
    authenticated=True
)
```

### Validation and Normalization

```python
from api.utils import UUIDGenerator

# Validate UUID format
is_valid = UUIDGenerator.is_valid_uuid("123e4567-e89b-12d3-a456-426614174000")

# Normalize UUID string
normalized = UUIDGenerator.normalize_uuid("123E4567-E89B-12D3-A456-426614174000")
# Returns: "123e4567-e89b-12d3-a456-426614174000"
```

## Integration with SecurityContext

The UUID generator is specifically designed to work with the updated SecurityContext schema:

```python
# SecurityContext now accepts string user_id (not just UUID type)
# This allows both UUID and username formats:

context1 = SecurityContext(
    user_id="123e4567-e89b-12d3-a456-426614174000",  # UUID format
    device_id="laptop_001",
    authenticated=True
)

context2 = SecurityContext(
    user_id="john_doe",  # Username format
    device_id="mobile_002",
    authenticated=True
)
```

## Class Reference

### UUIDGenerator

Main utility class with static methods:

- `generate_user_id()` → str: User UUID
- `generate_device_id(prefix=None)` → str: Device UUID with optional prefix
- `generate_session_id()` → str: Session UUID
- `generate_request_id()` → str: Request UUID
- `generate_space_id(space_type="personal")` → str: Space UUID with type prefix
- `generate_event_id()` → str: Event UUID
- `generate_secure_token(length=32)` → str: Secure hex token
- `is_valid_uuid(uuid_string)` → bool: UUID validation
- `normalize_uuid(uuid_string)` → str: UUID normalization
- `generate_username_to_uuid_mapping(username)` → str: Deterministic UUID from username

### Convenience Functions

- `new_user_id()` → str
- `new_device_id(prefix=None)` → str
- `new_session_id()` → str
- `new_request_id()` → str
- `new_space_id(space_type="personal")` → str
- `new_event_id()` → str
- `username_to_uuid(username)` → str
- `is_uuid(value)` → bool
- `create_dev_user_context(username, device_name="dev_device")` → dict

## Testing

Run the demo script:

```bash
cd g:\familyOS
python api/utils/uuid_generator.py
```

Import and test in Python:

```python
from api.utils import *

print("User ID:", new_user_id())
print("Device ID:", new_device_id('laptop'))
print("Username to UUID:", username_to_uuid('john_doe'))
```

## Development Notes

- UUIDs are generated using `uuid4()` for cryptographic security
- Username-to-UUID mapping uses `uuid5()` with NAMESPACE_OID for deterministic results
- Compatible with Python 3.11+ (no uuid7 dependency)
- Follows FamilyOS coding standards and type hints
- Integrated with existing authentication and policy systems

## Related Files

- `api/schemas.py` - SecurityContext schema that uses these UUIDs
- `api/middleware/auth.py` - Authentication middleware integration
- `policy/service.py` - Policy system that uses user IDs
- `tests/integration/test_auth_integration.py` - Integration tests
