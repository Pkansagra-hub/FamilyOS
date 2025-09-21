
from typing import Optional, Dict, Any
try:
    from events.bus import EventBus
    from events.types import Event, EventMeta
except Exception:
    EventBus = None
    Event = None
    EventMeta = None

_BUS: Optional[object] = None

def set_bus(bus) -> None:
    global _BUS
    _BUS = bus

async def publish_affect_update(person_id: str, space_id: str, payload: Dict[str, Any]) -> None:
    if _BUS is None or Event is None:
        return
    ev = Event(meta=EventMeta(topic="affect.update", type="AFFECT_UPDATE", space_id=space_id, actor=person_id), payload=payload)
    await _BUS.publish(ev)
