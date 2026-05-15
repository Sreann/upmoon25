from __future__ import annotations

from typing import Iterable, Tuple


def pointcloud_command_topics() -> Tuple[str, str]:
    """Return accepted point-cloud command topics (legacy + canonical)."""
    return ("/cmd/pointcloud", "cmd/pointcloud")


def pointcloud_stream_enabled(command_value: int) -> bool:
    """Interpret Int8 command payload for point-cloud streaming."""
    return int(command_value) != 0


def unique_topics(topics: Iterable[str]) -> Tuple[str, ...]:
    seen = []
    for topic in topics:
        if topic not in seen:
            seen.append(topic)
    return tuple(seen)
