from pathlib import Path
from typing import Any, Dict, Optional

import streamlit.components.v1 as components


_BUILD_DIR = Path(__file__).resolve().parent / "teleop_component" / "build"
_HOLD_COMPONENT = components.declare_component(
    "lunar_dashboard_hold_controls",
    path=str(_BUILD_DIR),
)

_BUTTONS = {
    "drive": [
        {"command": "forward", "label": "Forward", "hold": True},
        {"command": "back", "label": "Back", "hold": True},
        {"command": "left_arc", "label": "Left Arc", "hold": True},
        {"command": "right_arc", "label": "Right Arc", "hold": True},
        {"command": "stop", "label": "Stop", "hold": False, "variant": "danger"},
    ],
    "bucket_vel": [
        {"command": "forward", "label": "Bucket Forward", "hold": True},
        {"command": "reverse", "label": "Bucket Reverse", "hold": True},
        {"command": "stop", "label": "Bucket Stop", "hold": False, "variant": "danger"},
    ],
    "pan": [
        {"command": "left", "label": "Pan Left", "hold": True},
        {"command": "right", "label": "Pan Right", "hold": True},
        {"command": "stop", "label": "Pan Stop", "hold": False, "variant": "danger"},
    ],
}


def render_hold_controls(
    kind: str,
    *,
    disabled: bool = False,
    key: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    if kind not in _BUTTONS:
        raise ValueError(f"Unsupported hold control kind: {kind}")

    return _HOLD_COMPONENT(
        kind=kind,
        buttons=_BUTTONS[kind],
        disabled=disabled,
        key=key,
        default=None,
    )


def render_refresh_tick(
    *,
    interval_ms: int = 1000,
    key: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    return _HOLD_COMPONENT(
        mode="refresh",
        interval_ms=int(interval_ms),
        key=key,
        default=None,
    )


def render_camera_stream(
    *,
    stream_port: int,
    disabled: bool = False,
    key: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    return _HOLD_COMPONENT(
        mode="camera",
        stream_port=int(stream_port),
        disabled=disabled,
        key=key,
        default=None,
    )
