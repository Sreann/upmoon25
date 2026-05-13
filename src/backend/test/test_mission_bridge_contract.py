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
