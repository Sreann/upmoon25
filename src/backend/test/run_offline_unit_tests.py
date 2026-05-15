from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
BACKEND_SRC = ROOT / "src" / "backend"
FRONTEND_SRC = ROOT / "src" / "frontend"
LUNAR_SRC = ROOT / "lunar" / "src"

for path in [BACKEND_SRC, FRONTEND_SRC, LUNAR_SRC]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


TEST_FILES = [
    ROOT / "src" / "backend" / "test" / "test_terrain_grid_math.py",
    ROOT / "src" / "backend" / "test" / "test_flag_detection_math.py",
    ROOT / "src" / "backend" / "test" / "test_keyboard_trusted_paths.py",
    ROOT / "src" / "backend" / "test" / "test_global_mapper_tf.py",
    ROOT / "src" / "backend" / "test" / "test_navigation_controller_pure.py",
    ROOT / "src" / "backend" / "test" / "test_occupancy_grid_codec.py",
    ROOT / "src" / "backend" / "test" / "test_mission_bridge_contract.py",
    ROOT / "src" / "backend" / "test" / "test_autonomy_shadow_logic.py",
    ROOT / "src" / "backend" / "test" / "test_autonomy_topic_contracts.py",
    ROOT / "src" / "backend" / "test" / "test_nav_mission_pure.py",
    ROOT / "src" / "backend" / "test" / "test_encoder_drive_sequence.py",
    ROOT / "src" / "backend" / "test" / "test_dig_sequence_terrain_pure.py",
]


def _load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    spec.loader.exec_module(module)
    return module


def main() -> int:
    passed = 0
    for path in TEST_FILES:
        module = _load_module(path)
        for name in sorted(item for item in dir(module) if item.startswith("test_")):
            getattr(module, name)()
            passed += 1
            print(f"ok {path.name}::{name}")
    print(f"{passed} offline unit tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
