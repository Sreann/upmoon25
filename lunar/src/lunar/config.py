from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json


def find_repo_root(start: Path | None = None) -> Path:
    if start is None:
        start = Path(__file__).resolve()
    for p in [start, *start.parents]:
        if (p / "gz_worlds").exists() and (p / "src").exists():
            return p
    return start.parent


def state_dir() -> Path:
    root = find_repo_root()
    d = root / ".lunar"
    d.mkdir(exist_ok=True)
    return d


CONFIG_PATH = state_dir() / "config.json"


@dataclass
class Config:
    world_path: str
    port: int
    headless: bool
    bridge_cmd: str
    domain_id: int

    @staticmethod
    def default() -> "Config":
        root = find_repo_root()
        world = root / "gz_worlds" / "arena1.world"
        return Config(
            world_path=str(world),
            port=8765,
            headless=False,
            bridge_cmd="ros2 run foxglove_bridge foxglove_bridge",
            domain_id=25,
        )

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @staticmethod
    def load() -> "Config":
        if not CONFIG_PATH.exists():
            cfg = Config.default()
            cfg.save()
            return cfg
        data = json.loads(CONFIG_PATH.read_text())
        default = Config.default()
        return Config(
            world_path=data.get("world_path", default.world_path),
            port=int(data.get("port", default.port)),
            headless=bool(data.get("headless", default.headless)),
            bridge_cmd=data.get("bridge_cmd", default.bridge_cmd),
            domain_id=int(data.get("domain_id", default.domain_id)),
        )

    def save(self) -> None:
        CONFIG_PATH.write_text(self.to_json())
