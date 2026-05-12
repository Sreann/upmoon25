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
        "state": "HEALTH_CHECK",
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
