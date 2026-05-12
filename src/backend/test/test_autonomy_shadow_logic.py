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


def test_shadow_tick_odom_stale():
    out = compute_shadow_tick(
        paused=False,
        perception_health={"safety_ok": True},
        terrain_status={"ok": True},
        flag_candidates={},
        zone_marks={"dig": {}, "dump": {}},
        last_perception_time=1000.0,
        last_terrain_time=1000.0,
        last_flag_time=1000.0,
        last_odom_time=500.0,
        now_mono=1000.5,
        health_timeout_sec=2.0,
        terrain_timeout_sec=2.0,
        flag_timeout_sec=2.0,
    )
    assert out["state"] == "HEALTH_CHECK"
    assert "Odom" in out["stop_reason"]


def test_shadow_tick_perception_fail():
    out = compute_shadow_tick(
        paused=False,
        perception_health=None,
        terrain_status={"ok": True},
        flag_candidates={},
        zone_marks={"dig": {}, "dump": {}},
        last_perception_time=None,
        last_terrain_time=1000.0,
        last_flag_time=1000.0,
        last_odom_time=1000.0,
        now_mono=1000.5,
        health_timeout_sec=2.0,
        terrain_timeout_sec=2.0,
        flag_timeout_sec=2.0,
    )
    assert out["state"] == "HEALTH_CHECK"
    assert "Perception" in out["stop_reason"]


def test_shadow_tick_waits_for_zones_when_healthy():
    out = compute_shadow_tick(
        paused=False,
        perception_health={"safety_ok": True},
        terrain_status={"ok": True},
        flag_candidates={},
        zone_marks={},
        last_perception_time=1000.0,
        last_terrain_time=1000.0,
        last_flag_time=1000.0,
        last_odom_time=1000.0,
        now_mono=1000.5,
        health_timeout_sec=2.0,
        terrain_timeout_sec=2.0,
        flag_timeout_sec=2.0,
    )
    assert out["state"] == "WAIT_FOR_ZONE_MARKS"
    assert out["mode"] == "Assisted"


def test_shadow_tick_ready_all_inputs_no_motion_yet():
    out = compute_shadow_tick(
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
    )
    assert out["state"] == "PAUSED"
    assert "motion remains disabled" in out["stop_reason"]


def test_shadow_tick_paused_omits_stop_reason_key():
    out = compute_shadow_tick(
        paused=True,
        perception_health={"safety_ok": True},
        terrain_status={"ok": True},
        flag_candidates={},
        zone_marks={},
        last_perception_time=1000.0,
        last_terrain_time=1000.0,
        last_flag_time=1000.0,
        last_odom_time=1000.0,
        now_mono=1000.5,
        health_timeout_sec=2.0,
        terrain_timeout_sec=2.0,
        flag_timeout_sec=2.0,
    )
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
    assert u["state"] == "WAIT_FOR_ZONE_MARKS"


def test_parse_unknown():
    pub, u = parse_autonomy_command("launch-missiles", allow_motion=False)
    assert pub is False
    assert "Ignored" in u["last_decision"]
