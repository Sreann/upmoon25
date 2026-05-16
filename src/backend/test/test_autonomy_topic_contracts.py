"""Offline contracts for JSON blobs exchanged between autonomy nodes and mission bridge."""


def test_perception_health_top_level_contract():
    sample = {
        "stamp": 0.0,
        "safety_ok": True,
        "topics": [
            {
                "topic": "/camera/rgb/image_compressed",
                "status": "live",
                "age_sec": 0.1,
                "rate_hz": 15.0,
                "note": "front RGB",
                "safety_critical": False,
                "point_count": 0,
            }
        ],
    }
    assert "safety_ok" in sample
    assert isinstance(sample["topics"], list)
    for t in sample["topics"]:
        assert "topic" in t and "status" in t


def test_terrain_status_contract_for_supervisor_and_bridge():
    sample = {
        "stamp": 0.0,
        "ok": True,
        "note": "tf ok",
        "point_count": 1000,
        "obstacle_cells": 2,
        "caution_cells": 1,
        "unknown_cells": 5,
        "latency_ms": 12.0,
    }
    assert sample.get("ok") is True
    assert "obstacle_cells" in sample and "caution_cells" in sample


def test_flag_candidates_contract_for_supervisor_and_bridge():
    sample = {
        "stamp": 0.0,
        "image_topic": "/camera/rgb/image_compressed",
        "image_width": 640,
        "image_height": 480,
        "candidates": [{"bearing_deg": -5.0, "confidence": 0.8, "area_px": 400.0}],
    }
    cands = sample.get("candidates", [])
    assert isinstance(cands, list)
    if cands:
        assert "bearing_deg" in cands[0]


def test_autonomy_state_contract_keys():
    sample = {
        "stamp": 0.0,
        "mode": "Manual",
        "state": "PERCEPTION_FAULT",
        "armed": False,
        "estop": False,
        "confidence": 0.5,
        "cycle": 1,
        "payload": "unknown",
        "stop_reason": "",
        "last_decision": "",
        "next_transition": "",
        "zones": {},
    }
    for key in (
        "mode",
        "state",
        "armed",
        "estop",
        "confidence",
        "stop_reason",
        "last_decision",
        "next_transition",
        "zones",
    ):
        assert key in sample


def test_nav_mission_state_contract_keys():
    sample = {
        "stamp": 0.0,
        "phase": "FOLLOW_TO_DIG",
        "controller_mode": "corridor_follow",
        "detail": "follow_zone_goal",
        "dig_autonomy_enabled": False,
        "nav_controller_corridor_enabled": True,
        "unknown_fraction": 0.2,
        "dig_distance_m": 1.1,
    }
    for key in (
        "phase",
        "controller_mode",
        "detail",
        "dig_autonomy_enabled",
        "nav_controller_corridor_enabled",
    ):
        assert key in sample


def test_dig_sequence_state_contract_keys():
    sample = {
        "stamp": 0.0,
        "phase": "DRIVE_FORWARD",
        "wait_for_nav_dig_arm": False,
        "dig_arm": False,
        "ir_value": 10,
        "ir_target": 17,
        "ir_setup_mode": "le",
        "encoder_value": 50,
        "encoder_target": 120,
        "encoder_topic": "/sensor/encoder/left",
        "timed_drive_ms": 0,
        "drive_uses_encoder": True,
        "cycle_counter": 0,
        "max_cycles_le": 3,
        "bucket_pos_commanded": 22,
        "keep_bucket_chain_until_done": False,
        "bucket_chain_speed": 40,
        "phase_elapsed_sec": 0.5,
        "conveyor_remaining_sec": None,
        "use_local_terrain_grid": True,
        "terrain_had_grid": True,
        "terrain_fresh": True,
        "terrain_forward_ok": True,
        "terrain_reverse_ok": True,
        "terrain_gate_forward": "center_clear",
        "terrain_gate_reverse": "center_clear",
        "ir_bucket_gate_min_ir_drop": 2,
        "ir_bucket_gate_timeout_sec": 25.0,
        "ir_bucket_gate_waiting": False,
        "ir_anchor_before_last_bucket_step": -1,
        "ir_bucket_gate_elapsed_sec": None,
        "post_dump_bucket_bump_pending": False,
    }
    for key in (
        "phase",
        "wait_for_nav_dig_arm",
        "ir_value",
        "ir_target",
        "encoder_value",
        "encoder_target",
        "encoder_topic",
        "cycle_counter",
        "max_cycles_le",
        "bucket_pos_commanded",
        "phase_elapsed_sec",
        "use_local_terrain_grid",
        "terrain_forward_ok",
    ):
        assert key in sample
