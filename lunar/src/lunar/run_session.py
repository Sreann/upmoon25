"""Per-run session folders for ``lunar run`` (combined logs + optional rosbag)."""

from __future__ import annotations

import shlex
import subprocess
import time
from datetime import datetime
from pathlib import Path


def runs_root(repo_root: Path) -> Path:
    return repo_root / ".lunar" / "runs"


def create_run_session(repo_root: Path, profile: str) -> tuple[Path, Path]:
    """
    Create ``.lunar/runs/<timestamp>_<profile>/`` with ``combined.log`` header.

    Returns ``(session_dir, combined_log_path)``.
    """
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    session_dir = runs_root(repo_root) / f"{stamp}_{profile}"
    try:
        session_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        session_dir = runs_root(repo_root) / f"{stamp}_{profile}_{int(time.time() * 1e6)}"
        session_dir.mkdir(parents=True, exist_ok=False)
    combined = session_dir / "combined.log"
    banner = (
        f"=== lunar run session ===\n"
        f"profile: {profile}\n"
        f"started: {time.ctime()}\n"
        f"repo: {repo_root}\n"
        f"=========================\n\n"
    )
    combined.write_text(banner, encoding="utf-8")
    _write_readme(session_dir)
    _link_latest(repo_root, session_dir)
    return session_dir, combined


def append_process_banner(combined_log: Path, name: str, cmd: str) -> None:
    with combined_log.open("a", encoding="utf-8") as handle:
        handle.write(f"\n### [{name}] {time.strftime('%H:%M:%S')}\n{cmd}\n\n")


def write_run_meta(
    session_dir: Path,
    repo_root: Path,
    *,
    profile: str,
    commands: list[tuple[str, str]],
    session_bag: bool,
    session_bag_depth: bool,
) -> None:
    lines = [
        f"profile={profile}",
        f"captured_at={time.ctime()}",
        f"session_bag={session_bag}",
        f"session_bag_depth={session_bag_depth}",
        "",
        "git_head=",
    ]
    try:
        cp = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=3.0,
        )
        if cp.returncode == 0 and cp.stdout.strip():
            lines[-1] = f"git_head={cp.stdout.strip()}"
    except (OSError, subprocess.TimeoutExpired, FileNotFoundError):
        lines[-1] = "git_head=(unavailable)"

    lines.extend(["", "processes:"])
    for name, cmd in commands:
        lines.append(f"  [{name}] {cmd}")

    (session_dir / "RUN_META.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def ros_bag_topics(profile: str, *, include_depth: bool) -> list[str]:
    """Curated topics for post-run analysis (shareable; depth optional due to size)."""
    topics = [
        "/odom",
        "/tf",
        "/tf_static",
        "/cmd/velocity",
        "/autonomy/state",
        "/autonomy/perception_health",
        "/autonomy/terrain_status",
        "/autonomy/local_terrain_grid",
        "/autonomy/navigation_twist",
        "/autonomy/navigation_status",
        "/autonomy/navigation_active",
        "/autonomy/nav_mission/state",
        "/autonomy/nav_mission_twist",
        "/autonomy/zone_mark",
        "/perception/flag_candidates",
        "/cmd/pan",
    ]
    if profile == "nav-dig":
        topics.extend(
            [
                "/autonomy/dig_arm",
                "/autonomy/dig_sequence/state",
            ]
        )
    if include_depth:
        topics.append("/camera/depth/points")
    # de-dupe preserving order
    seen: set[str] = set()
    out: list[str] = []
    for t in topics:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def bag_record_command(repo_root: Path, session_dir: Path, ros_env_chain: str, profile: str, *, include_depth: bool) -> str:
    """Single bash command: source ROS + workspace, then ``ros2 bag record`` into ``session_dir/rosbag``."""
    topics = ros_bag_topics(profile, include_depth=include_depth)
    out_dir = session_dir / "rosbag"
    topic_args = " ".join(shlex.quote(t) for t in topics)
    return (
        f"cd {shlex.quote(str(repo_root))} && {ros_env_chain} && "
        f"ros2 bag record -o {shlex.quote(str(out_dir))} {topic_args}"
    )


def _write_readme(session_dir: Path) -> None:
    (session_dir / "README.txt").write_text(
        "This folder is one `lunar run` session.\n\n"
        "  combined.log  — stdout/stderr from every process lunar spawned (interleaved).\n"
        "  RUN_META.txt  — profile, git HEAD if available, and exact launch commands.\n"
        "  rosbag/       — present if you used --session-bag (MCAP/SQLite bag per ROS distro).\n\n"
        "Share for debugging: zip this entire folder (e.g. `zip -r run.zip .` from inside it).\n"
        "If you also ran `lunar run robot` or `mission-bridge` in another shell, grab that\n"
        "session folder from `.lunar/runs/` too — each `lunar run` only logs its own children.\n",
        encoding="utf-8",
    )


def _link_latest(repo_root: Path, session_dir: Path) -> None:
    link = runs_root(repo_root) / "latest"
    try:
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(session_dir.name, target_is_directory=True)
    except OSError:
        # Windows or permission: skip
        pass
