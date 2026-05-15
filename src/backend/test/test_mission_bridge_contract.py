from pathlib import Path
import sys
import time

LUNAR_SRC = Path(__file__).resolve().parents[3] / "lunar" / "src"
if str(LUNAR_SRC) not in sys.path:
    sys.path.insert(0, str(LUNAR_SRC))

from lunar import mission_bridge


def test_stream_status_from_missing_age_is_missing():
    status, age_ms = mission_bridge._stream_status_from_age(None)

    assert status == "missing"
    assert age_ms is None


def test_stream_status_marks_fresh_sample_live():
    status, age_ms = mission_bridge._stream_status_from_age(time.time())

    assert status == "live"
    assert age_ms is not None
    assert age_ms >= 0


def test_build_snapshot_includes_required_dashboard_contract_sections():
    snapshot = mission_bridge.build_snapshot()

    for key in [
        "mission",
        "metrics",
        "topics",
        "cameras",
        "hardware",
        "zones",
        "logs",
        "trends",
        "sensors",
        "pid",
        "audit",
        "terrainGrid",
        "zoneMarking",
        "rawConfig",
    ]:
        assert key in snapshot


def test_build_snapshot_exposes_terrain_grid_when_bridge_state_has_grid():
    mission_bridge._state.terrain_status = {"ok": True, "note": "unit test terrain"}
    mission_bridge._state.terrain_grid = {
        "last_seen": time.time(),
        "width": 2,
        "height": 2,
        "resolution": 0.1,
        "frame_id": "base_link",
        "cells": [0, 100, 60, -1],
        "obstacle_cells": 1,
        "caution_cells": 1,
        "unknown_cells": 1,
    }

    snapshot = mission_bridge.build_snapshot()

    assert snapshot["terrainGrid"]["status"] == "live"
    assert snapshot["terrainGrid"]["width"] == 2
    assert snapshot["terrainGrid"]["height"] == 2
    assert snapshot["terrainGrid"]["cells"] == [0, 100, 60, -1]
    assert snapshot["terrainGrid"]["obstacleCells"] == 1
    assert snapshot["terrainGrid"]["cautionCells"] == 1
    assert snapshot["terrainGrid"]["unknownCells"] == 1

    mission_bridge._state.terrain_status = None
    mission_bridge._state.terrain_grid = None


def test_camera_topics_exclude_deprecated_tracking_camera():
    assert set(mission_bridge.CAMERA_TOPICS.keys()) == {"front", "rear"}
    assert "/camera/tracking/image_compressed" not in mission_bridge.CAMERA_TOPICS.values()


def test_build_snapshot_cameras_are_only_front_and_rear_streams():
    snapshot = mission_bridge.build_snapshot()
    ids = [c["id"] for c in snapshot["cameras"]]
    assert ids == ["front", "rear"]
    assert "tracking" not in ids
    topics = [c["topic"] for c in snapshot["cameras"]]
    assert "/camera/rgb/image_compressed" in topics
    assert "/camera/rear/image_compressed" in topics


def test_build_snapshot_mission_includes_navigation_active():
    mission_bridge._state.navigation_active = True
    snap = mission_bridge.build_snapshot()
    assert "navigationActive" in snap["mission"]
    assert snap["mission"]["navigationActive"] is True
    mission_bridge._state.navigation_active = False


def test_build_snapshot_mission_includes_nav_mission_when_set():
    mission_bridge._state.nav_mission_state = {
        "phase": "AT_DIG_HANDOFF",
        "controller_mode": "none",
        "dig_autonomy_enabled": True,
        "nav_controller_corridor_enabled": False,
    }
    snap = mission_bridge.build_snapshot()
    nm = snap["mission"]["navMission"]
    assert nm is not None
    assert nm["phase"] == "AT_DIG_HANDOFF"
    assert nm["controllerMode"] == "none"
    assert nm["digAutonomyEnabled"] is True
    assert nm["navCorridorEnabled"] is False
    mission_bridge._state.nav_mission_state = None


def test_build_snapshot_mission_nav_mission_key_present_when_cleared():
    mission_bridge._state.nav_mission_state = None
    snap = mission_bridge.build_snapshot()
    assert "navMission" in snap["mission"]
    assert snap["mission"]["navMission"] is None


def test_build_snapshot_mission_includes_dig_sequence_when_set():
    mission_bridge._state.dig_sequence_state = {
        "phase": "CONVEYOR_DUMP",
        "wait_for_nav_dig_arm": False,
        "dig_arm": False,
        "ir_value": 17,
        "ir_target": 17,
        "ir_setup_mode": "le",
        "encoder_value": 0,
        "encoder_target": 120,
        "encoder_topic": "/sensor/encoder/left",
        "cycle_counter": 2,
        "max_cycles_le": 5,
        "bucket_pos_commanded": 26,
        "keep_bucket_chain_until_done": False,
        "bucket_chain_speed": 40,
        "phase_elapsed_sec": 1.5,
        "conveyor_remaining_sec": 2.1,
        "use_local_terrain_grid": True,
        "terrain_had_grid": True,
        "terrain_fresh": True,
        "terrain_forward_ok": False,
        "terrain_reverse_ok": True,
        "terrain_gate_forward": "blocked",
        "terrain_gate_reverse": "center_clear",
        "ir_bucket_gate_min_ir_drop": 2,
        "ir_bucket_gate_timeout_sec": 25.0,
        "ir_bucket_gate_waiting": False,
        "ir_anchor_before_last_bucket_step": 70,
        "ir_bucket_gate_elapsed_sec": None,
        "post_dump_bucket_bump_pending": False,
    }
    snap = mission_bridge.build_snapshot()
    ds = snap["mission"]["digSequence"]
    assert ds is not None
    assert ds["phase"] == "CONVEYOR_DUMP"
    assert ds["waitForNavDigArm"] is False
    assert ds["encoderTopic"] == "/sensor/encoder/left"
    assert ds["conveyorRemainingSec"] == 2.1
    assert ds["useLocalTerrainGrid"] is True
    assert ds["terrainForwardOk"] is False
    assert ds["terrainGateForward"] == "blocked"
    assert ds["irSetupMode"] == "le"
    assert ds["irBucketGateWaiting"] is False
    assert ds["postDumpBucketBumpPending"] is False
    assert ds["bucketChainSpeed"] == 40
    mission_bridge._state.dig_sequence_state = None


def test_build_snapshot_mission_dig_sequence_key_present_when_cleared():
    mission_bridge._state.dig_sequence_state = None
    snap = mission_bridge.build_snapshot()
    assert "digSequence" in snap["mission"]
    assert snap["mission"]["digSequence"] is None


def test_build_snapshot_navigation_steering_from_status():
    mission_bridge._state.navigation_status = {
        "linear_x": 0.12,
        "angular_z": -0.05,
        "plan_reason": "center_clear",
        "gated_reason": "",
    }
    mission_bridge._state.navigation_status_seen = time.time()
    snap = mission_bridge.build_snapshot()
    steer = snap["mission"]["navigationSteering"]
    assert steer is not None
    assert steer["linearX"] == 0.12
    assert steer["angularZ"] == -0.05
    assert steer["reason"] == "center_clear"
    assert steer["ageMs"] is not None
    mission_bridge._state.navigation_status = None
    mission_bridge._state.navigation_status_seen = None


def test_drive_scale_clamps_speed_limit_percent():
    assert mission_bridge._drive_scale(50.0) == 0.5
    assert mission_bridge._drive_scale(0.0) == 0.0
    assert mission_bridge._drive_scale(100.0) == 1.0
    assert mission_bridge._drive_scale(150.0) == 1.0
