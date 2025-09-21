"""Event utility functions."""

from uuid import uuid4


def generate_event_id() -> str:
    """Generate a unique event ID with format 'ev-' + 16-char hex.
    
    Returns:
        String formatted as "ev-" followed by a 16-character hexadecimal string.
    
    Example:
        >>> event_id = generate_event_id()
        >>> assert event_id.startswith('ev-')
        >>> assert len(event_id) == 19  # 'ev-' + 16 chars
        >>> assert all(c in '0123456789abcdef' for c in event_id[3:])
    """
    # Generate UUID and take first 16 chars of hex representation (without dashes)
    hex_part = uuid4().hex[:16]
    return f"ev-{hex_part}"