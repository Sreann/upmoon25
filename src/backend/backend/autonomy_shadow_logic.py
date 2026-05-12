"""
Shadow-mode autonomy state + confidence (no rclpy).

The ROS node `autonomy_supervisor` composes this with subscriptions and timing.
Unit tests cover this module without a live graph.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


def monotonic_fresh(ts: Optional[float], now_mono: float, timeout_sec: float) -> bool:
    if ts is None:
        return False
    return (now_mono - ts) <= timeout_sec


def compute_confidence(
    *,
    perception_ok: bool,
    perception_fresh: bool,
    terrain_ok: bool,
    terrain_fresh: bool,
    odom_ok: bool,
    dump_known: bool,
    dig_known: bool,
) -> float:
    score = 0.0
    score += 0.25 if perception_ok and perception_fresh else 0.0
    score += 0.25 if terrain_ok and terrain_fresh else 0.0
    score += 0.20 if odom_ok else 0.0
    score += 0.15 if dump_known else 0.0
    score += 0.15 if dig_known else 0.0
    return round(score, 2)


def next_transition_hint(
    *,
    flags_fresh: bool,
    flag_candidates: Optional[Dict[str, Any]],
) -> str:
    if flags_fresh and flag_candidates:
        candidates = flag_candidates.get("candidates", [])
        if candidates:
            best = candidates[0]
            return (
                f"Confirm dump flag bearing {best.get('bearing_deg')} deg, "
                f"confidence {best.get('confidence')}."
            )
        return "No flag candidates; use operator zone mark."
    return "Collect/refresh flag detections and zone marks."


def compute_shadow_tick(
    *,
    paused: bool,
    perception_health: Optional[Dict[str, Any]],
    terrain_status: Optional[Dict[str, Any]],
    flag_candidates: Optional[Dict[str, Any]],
    zone_marks: Dict[str, Any],
    last_perception_time: Optional[float],
    last_terrain_time: Optional[float],
    last_flag_time: Optional[float],
    last_odom_time: Optional[float],
    now_mono: float,
    health_timeout_sec: float,
    terrain_timeout_sec: float,
    flag_timeout_sec: float,
) -> Dict[str, Any]:
    """
    Returns: confidence, state, mode, stop_reason, last_decision, next_transition
    (mirrors one supervisor tick when not in ESTOP).
    """
    perception_ok = bool(perception_health and perception_health.get("safety_ok"))
    terrain_ok = bool(terrain_status and terrain_status.get("ok"))
    odom_ok = monotonic_fresh(last_odom_time, now_mono, health_timeout_sec)
    perception_fresh = monotonic_fresh(last_perception_time, now_mono, health_timeout_sec)
    terrain_fresh = monotonic_fresh(last_terrain_time, now_mono, terrain_timeout_sec)
    flags_fresh = monotonic_fresh(last_flag_time, now_mono, flag_timeout_sec)
    dump_known = "dump" in zone_marks or bool((flag_candidates or {}).get("candidates"))
    dig_known = "dig" in zone_marks

    confidence = compute_confidence(
        perception_ok=perception_ok,
        perception_fresh=perception_fresh,
        terrain_ok=terrain_ok,
        terrain_fresh=terrain_fresh,
        odom_ok=odom_ok,
        dump_known=dump_known,
        dig_known=dig_known,
    )
    next_tr = next_transition_hint(flags_fresh=flags_fresh, flag_candidates=flag_candidates)

    if paused:
        # Do not include stop_reason — paused tick preserves prior operator/context reason.
        return {
            "confidence": confidence,
            "state": "PAUSED",
            "mode": "Paused",
            "last_decision": "Holding because operator paused or took manual control.",
            "next_transition": next_tr,
        }
    if not perception_ok or not perception_fresh:
        return {
            "confidence": confidence,
            "state": "HEALTH_CHECK",
            "mode": "Manual",
            "stop_reason": "Perception health is missing, stale, or unsafe.",
            "last_decision": "Do not arm autonomy.",
            "next_transition": next_tr,
        }
    if not odom_ok:
        return {
            "confidence": confidence,
            "state": "HEALTH_CHECK",
            "mode": "Manual",
            "stop_reason": "Odom/localization is not fresh.",
            "last_decision": "Do not navigate without pose freshness.",
            "next_transition": next_tr,
        }
    if not terrain_ok or not terrain_fresh:
        return {
            "confidence": confidence,
            "state": "HEALTH_CHECK",
            "mode": "Manual",
            "stop_reason": "Local terrain grid is missing or unhealthy.",
            "last_decision": "Do not drive without local hazard layer.",
            "next_transition": next_tr,
        }
    if not dump_known or not dig_known:
        return {
            "confidence": confidence,
            "state": "WAIT_FOR_ZONE_MARKS",
            "mode": "Assisted",
            "stop_reason": "Need dig and dump zone marks or detections.",
            "last_decision": "Ask operator to mark zones or confirm flag detections.",
            "next_transition": next_tr,
        }
    return {
        "confidence": confidence,
        "state": "PAUSED",
        "mode": "Assisted",
        "stop_reason": "All prerequisites look plausible, but motion remains disabled.",
        "last_decision": "Ready for short-segment autonomy implementation.",
        "next_transition": next_tr,
    }


def parse_autonomy_command(command: str, allow_motion: bool) -> Tuple[bool, Dict[str, Any]]:
    """
    Parse `/cmd/autonomy` string command.

    Returns:
        (publish_zero_twist, field_updates) — apply updates with setattr on the node.
    """
    cmd = command.strip().lower()
    if cmd in {"estop", "abort"}:
        return True, {
            "estop": True,
            "paused": True,
            "mode": "Estop",
            "state": "ESTOP",
            "stop_reason": "Operator stop command received on /cmd/autonomy.",
        }
    if cmd == "pause":
        return True, {
            "paused": True,
            "mode": "Paused",
            "state": "PAUSED",
            "stop_reason": "Autonomy paused by operator.",
        }
    if cmd == "manual":
        return True, {
            "paused": True,
            "mode": "Manual",
            "state": "PAUSED",
            "stop_reason": "Manual takeover requested.",
        }
    if cmd == "reset":
        return False, {
            "estop": False,
            "paused": False,
            "mode": "Manual",
            "state": "HEALTH_CHECK",
            "stop_reason": "Supervisor reset; checking health.",
        }
    if cmd == "arm":
        if not allow_motion:
            return False, {
                "last_decision": "Arm rejected: allow_motion is false.",
                "stop_reason": "Shadow mode only; autonomous drive is disabled.",
            }
        return False, {
            "mode": "Auto",
            "state": "WAIT_FOR_ZONE_MARKS",
            "stop_reason": "Armed, waiting for zones.",
        }
    return False, {"last_decision": f"Ignored unknown autonomy command: {command}"}
