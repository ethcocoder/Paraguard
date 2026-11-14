from dataclasses import dataclass
import math
from typing import Any, Mapping


@dataclass(frozen=True)
class Event:
    timestamp: float
    process_id: str
    channel: str
    event_type: str = ""

    @classmethod
    def from_mapping(cls, record: Mapping[str, Any]) -> "Event":
        try:
            timestamp = float(record["timestamp"])
            process_id = str(record["process_id"]).strip()
            channel = str(record["channel"]).strip()
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("each event needs timestamp, process_id, and channel") from error
        if not math.isfinite(timestamp):
            raise ValueError("timestamp must be finite")
        if not process_id or not channel:
            raise ValueError("process_id and channel must not be empty")
        event_type = str(record.get("event_type", "")).strip()
        return cls(timestamp, process_id, channel, event_type)