from __future__ import annotations

from frontend.depth_control import pointcloud_command_topics, pointcloud_stream_enabled, unique_topics


def test_pointcloud_stream_enabled_interprets_zero_as_pause():
    assert pointcloud_stream_enabled(0) is False
    assert pointcloud_stream_enabled(1) is True
    assert pointcloud_stream_enabled(-1) is True


def test_pointcloud_command_topics_includes_legacy_and_canonical():
    topics = pointcloud_command_topics()
    assert "/cmd/pointcloud" in topics
    assert "cmd/pointcloud" in topics


def test_unique_topics_deduplicates_preserving_order():
    assert unique_topics(("a", "b", "a", "c")) == ("a", "b", "c")
