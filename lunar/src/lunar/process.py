from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os
import signal
import subprocess
from typing import List

from .config import state_dir

STATE_PATH = state_dir() / "state.json"


@dataclass
class ProcInfo:
    name: str
    pid: int
    pgid: int
    cmd: str
    proc: subprocess.Popen | None = None


def _write_state(procs: List[ProcInfo]) -> None:
    # Don't try to serialize the Popen object
    data = []
    for p in procs:
        d = p.__dict__.copy()
        d.pop("proc", None)
        data.append(d)
    STATE_PATH.write_text(json.dumps(data, indent=2))


def _read_state() -> List[ProcInfo]:
    if not STATE_PATH.exists():
        return []
    data = json.loads(STATE_PATH.read_text())
    return [ProcInfo(**d) for d in data]


def spawn(name: str, cmd: str, log_file: Path | None = None) -> ProcInfo:
    stdout_dest = subprocess.PIPE
    if log_file:
        stdout_dest = open(log_file, "a")

    # Capture current environment (including DISPLAY and ROS variables)
    env = os.environ.copy()

    p = subprocess.Popen(
        cmd,
        shell=True,
        executable="/bin/bash",
        preexec_fn=os.setsid,
        stdout=stdout_dest,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,  # Line buffered
        env=env
    )
    pgid = os.getpgid(p.pid)
    info = ProcInfo(name=name, pid=p.pid, pgid=pgid, cmd=cmd, proc=p)
    return info


def save_state(procs: List[ProcInfo]) -> None:
    _write_state(procs)


def _cmdline_for_pid(pid: int) -> str:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return ""
    return raw.replace(b"\x00", b" ").decode("utf-8", errors="ignore").strip()


def kill_all() -> List[str]:
    msgs = []
    procs = _read_state()
    current_pgid = os.getpgrp()
    for p in procs:
        try:
            if p.pgid == current_pgid:
                msgs.append(f"skipped current process group for {p.name} (pgid {p.pgid})")
                continue

            if os.getpgid(p.pid) != p.pgid:
                msgs.append(f"stale process record for {p.name} (pid {p.pid}, pgid {p.pgid})")
                continue

            cmdline = _cmdline_for_pid(p.pid)
            if cmdline and p.cmd not in cmdline:
                msgs.append(f"stale command record for {p.name} (pid {p.pid})")
                continue

            os.killpg(p.pgid, signal.SIGTERM)
            msgs.append(f"sent SIGTERM to {p.name} (pgid {p.pgid})")
        except (ProcessLookupError, PermissionError):
            msgs.append(f"process group not found for {p.name} (pgid {p.pgid})")
    if STATE_PATH.exists():
        STATE_PATH.unlink()
    return msgs
