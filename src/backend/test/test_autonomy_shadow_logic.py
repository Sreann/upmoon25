"""Offline tests for shadow autonomy state machine (no ROS graph)."""

from backend.autonomy_shadow_logic import (
    compute_confidence,
    compute_shadow_tick,
    monotonic_fresh,
    next_transition_hint,
    parse_autonomy_command,
)


def test_monotonic_fresh():
    assert monotonic_fresh(100.0, 101.0, 2.0) is True
    assert monotonic_fresh(100.0, 103.5, 2.0) is False
    assert monotonic_fresh(None, 100.0, 2.0) is False


def test_compute_confidence_full_grid():
    assert (
        compute_confidence(
            perception_ok=True,
            perception_fresh=True,
            terrain_ok=True,
            terrain_fresh=True,
            odom_ok=True,
            dump_known=True,
            dig_known=True,
        )
        == 1.0
    )


def test_compute_confidence_partial():
    assert (
        compute_confidence(
            perception_ok=True,
            perception_fresh=True,
            terrain_ok=False,
            terrain_fresh=False,
            odom_ok=True,
            dump_known=False,
            dig_known=False,
        )
        == 0.45
    )


def test_next_transition_hint_with_candidate():
    hint = next_transition_hint(
        flags_fresh=True,
        flag_candidates={"candidates": [{"bearing_deg": 12.5, "confidence": 0.9}]},
    )
    assert "12.5" in hint
    assert "0.9" in hint


def _base_kwargs(**over):
    base = dict(
        paused=False,
        perception_health={"safety_ok": True},
        terrain_status={"ok": True},
        flag_candidates={},
        zone_marks={"dig": {"zone": "dig"}, "dump": {"zone": "dump"}},
        last_perception_time=1000.0,
        last_terrain_time=1000.0,
        last_flag_time=1000.0,
        last_odom_time=1000.0,
        now_mono=1000.5,
        health_timeout_sec=2.0,
        terrain_timeout_sec=2.0,
        flag_timeout_sec=2.0,
        navigation_active=False,
    )
    base.update(over)
    return base


def test_shadow_tick_odom_stale():
    out = compute_shadow_tick(
        **_base_kwargs(
            last_odom_time=500.0,
            zone_marks={"dig": {}, "dump": {}},
        )
    )
    assert out["state"] == "LOCALIZATION_LOST"
    assert "Odom" in out["stop_reason"]


def test_shadow_tick_perception_missing():
    out = compute_shadow_tick(
        **_base_kwargs(
            perception_health=None,
            last_perception_time=None,
            zone_marks={"dig": {}, "dump": {}},
        )
    )
    assert out["state"] == "PERCEPTION_FAULT"


def test_shadow_tick_perception_stale():
    out = compute_shadow_tick(
        **_base_kwargs(
            last_perception_time=500.0,
            zone_marks={"dig": {}, "dump": {}},
        )
    )
    assert out["state"] == "PERCEPTION_STALE"


def test_shadow_tick_perception_unsafe():
    out = compute_shadow_tick(
        **_base_kwargs(
            perception_health={"safety_ok": False},
            zone_marks={"dig": {}, "dump": {}},
        )
    )
    assert out["state"] == "PERCEPTION_FAULT"


def test_shadow_tick_terrain_missing():
    out = compute_shadow_tick(
        **_base_kwargs(
            terrain_status=None,
            zone_marks={"dig": {}, "dump": {}},
        )
    )
    assert out["state"] == "TERRAIN_FAULT"


def test_shadow_tick_terrain_stale():
    out = compute_shadow_tick(
        **_base_kwargs(
            last_terrain_time=500.0,
            zone_marks={"dig": {}, "dump": {}},
        )
    )
    assert out["state"] == "TERRAIN_STALE"


def test_shadow_tick_waits_for_dig_mark_when_healthy():
    out = compute_shadow_tick(**_base_kwargs(zone_marks={}))
    assert out["state"] == "AWAIT_MARK_DIG"
    assert out["mode"] == "Assisted"


def test_shadow_tick_waits_for_dump_when_dig_marked():
    out = compute_shadow_tick(**_base_kwargs(zone_marks={"dig": {"zone": "dig"}}))
    assert out["state"] == "AWAIT_MARK_DUMP"


def test_shadow_tick_nav_ready_when_gates_pass_nav_not_armed():
    out = compute_shadow_tick(**_base_kwargs(navigation_active=False))
    assert out["state"] == "NAV_READY"
    assert out.get("stop_reason", "") == ""
    assert "navigation_active" in out["last_decision"]


def test_shadow_tick_nav_active_when_controller_armed():
    out = compute_shadow_tick(**_base_kwargs(navigation_active=True))
    assert out["state"] == "NAV_ACTIVE"
    assert out.get("stop_reason", "") == ""


def test_shadow_tick_dump_from_flags_only():
    out = compute_shadow_tick(
        **_base_kwargs(
            zone_marks={"dig": {"zone": "dig"}},
            flag_candidates={"candidates": [{"bearing_deg": 1.0, "confidence": 0.5}]},
        )
    )
    assert out["state"] == "NAV_READY"


def test_shadow_tick_paused_omits_stop_reason_key():
    out = compute_shadow_tick(**_base_kwargs(paused=True, zone_marks={}))
    assert "stop_reason" not in out


def test_parse_estop():
    pub, u = parse_autonomy_command("estop", allow_motion=False)
    assert pub is True
    assert u["estop"] is True and u["state"] == "ESTOP"


def test_parse_arm_rejected_without_allow_motion():
    pub, u = parse_autonomy_command("arm", allow_motion=False)
    assert pub is False
    assert "rejected" in u["last_decision"]


def test_parse_arm_accepted():
    pub, u = parse_autonomy_command("arm", allow_motion=True)
    assert pub is False
    assert u["mode"] == "Auto"
    assert u["state"] == "AWAIT_MARK_DIG"


def test_parse_unknown():
    pub, u = parse_autonomy_command("launch-missiles", allow_motion=False)
    assert pub is False
    assert "Ignored" in u["last_decision"]
