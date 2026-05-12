from pathlib import Path
import importlib.util
import json
import re
import subprocess
import sys
import textwrap
import time

import streamlit as st
import tomli


T265_SERIAL = "943222111294"
FRONT_D435_SERIAL = "018322071465"
REAR_D435_SERIAL = "018322071045"
D435_SERIALS = {FRONT_D435_SERIAL, REAR_D435_SERIAL}
DRIVE_PORTS = {
    "left": ["/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyACM2"],
    "right": ["/dev/ttyACM1", "/dev/ttyACM2", "/dev/ttyACM0"],
}
MINING_SPIN_PORTS = ["/dev/ttyUSB1", "/dev/ttyUSB0"]
ARDUINO_FALLBACK_PORTS = ["/dev/ttyACM2", "/dev/ttyACM1", "/dev/ttyACM0", "/dev/ttyUSB0"]
ARDUINO_VID = "2341"
ARDUINO_PID = "0043"


def _on_jetson() -> bool:
    return Path("/etc/nv_tegra_release").exists()


def _import_available(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except Exception:
        return False


def _load_realsense_module():
    try:
        import pyrealsense2 as rs
        if hasattr(rs, "pipeline") and hasattr(rs, "context"):
            return rs
    except Exception:
        pass

    try:
        from pyrealsense2 import pyrealsense2 as rs
        if hasattr(rs, "pipeline") and hasattr(rs, "context"):
            return rs
    except Exception:
        pass

    system_dist = "/usr/lib/python3/dist-packages"
    if system_dist not in sys.path and Path(system_dist).exists():
        sys.path.append(system_dist)

    try:
        import pyrealsense2 as rs
        if hasattr(rs, "pipeline") and hasattr(rs, "context"):
            return rs
    except Exception:
        pass

    try:
        from pyrealsense2 import pyrealsense2 as rs
        if hasattr(rs, "pipeline") and hasattr(rs, "context"):
            return rs
    except Exception:
        pass

    return None


_REALSENSE_CACHE = {
    "ts": 0.0,
    "value": {
        "driver_ok": False,
        "devices": [],
        "tracking_connected": False,
        "front_connected": False,
        "rear_connected": False,
    },
}


def _detect_realsense_via_system_python():
    script = textwrap.dedent(
        """
        import json

        T265_SERIAL = {t265_serial!r}
        FRONT_D435_SERIAL = {front_d435_serial!r}
        REAR_D435_SERIAL = {rear_d435_serial!r}

        result = {{
            "driver_ok": False,
            "devices": [],
            "tracking_connected": False,
            "front_connected": False,
            "rear_connected": False,
        }}

        try:
            import pyrealsense2 as rs
            if not (hasattr(rs, "pipeline") and hasattr(rs, "context")):
                raise ImportError("pyrealsense2 namespace package without bindings")
        except Exception:
            try:
                from pyrealsense2 import pyrealsense2 as rs
            except Exception:
                print(json.dumps(result))
                raise SystemExit(0)

        result["driver_ok"] = True
        try:
            ctx = rs.context()
            for dev in ctx.query_devices():
                name = dev.get_info(rs.camera_info.name)
                serial = dev.get_info(rs.camera_info.serial_number)
                result["devices"].append({{"name": name, "serial": serial}})
                upper_name = name.upper()
                if serial == T265_SERIAL or "T265" in upper_name or "TRACKING" in upper_name:
                    result["tracking_connected"] = True
                if serial == FRONT_D435_SERIAL:
                    result["front_connected"] = True
                if serial == REAR_D435_SERIAL:
                    result["rear_connected"] = True
        except Exception:
            pass

        print(json.dumps(result))
        """
    ).format(
        t265_serial=T265_SERIAL,
        front_d435_serial=FRONT_D435_SERIAL,
        rear_d435_serial=REAR_D435_SERIAL,
    )
    try:
        proc = subprocess.run(
            ["/usr/bin/python3", "-c", script],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        output = proc.stdout.strip()
        if not output:
            return {
                "driver_ok": False,
                "devices": [],
                "tracking_connected": False,
                "front_connected": False,
                "rear_connected": False,
            }

        # Some system Python environments print extra warnings before the JSON payload.
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        for line in reversed(lines):
            if line.startswith("{") and line.endswith("}"):
                return json.loads(line)

        match = re.search(r"(\{.*\})", output, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        return {
            "driver_ok": False,
            "devices": [],
            "tracking_connected": False,
            "front_connected": False,
            "rear_connected": False,
        }
    except Exception:
        return {
            "driver_ok": False,
            "devices": [],
            "tracking_connected": False,
            "front_connected": False,
            "rear_connected": False,
        }


def _first_existing_path(paths):
    for path in paths:
        if Path(path).exists():
            return path
    return None


def _serial_symlink_lookup(dirname):
    root = Path(f"/dev/serial/{dirname}")
    if not root.exists():
        return {}

    mapping = {}
    for entry in root.iterdir():
        try:
            mapping[str(entry.resolve())] = str(entry)
        except OSError:
            continue
    return mapping


def _discover_drive_ports():
    try:
        import serial.tools.list_ports
    except Exception:
        return {"left": None, "right": None}

    by_path = _serial_symlink_lookup("by-path")
    by_id = _serial_symlink_lookup("by-id")
    candidates = []
    for port in serial.tools.list_ports.comports():
        vid = None if port.vid is None else f"{port.vid:04x}"
        pid = None if port.pid is None else f"{port.pid:04x}"
        if vid == ARDUINO_VID and pid == ARDUINO_PID:
            continue

        device = str(port.device)
        text = " ".join(
            str(value or "")
            for value in (port.description, port.manufacturer, port.product, port.hwid, port.interface)
        ).lower()
        if not (device.startswith("/dev/ttyACM") or "sabertooth" in text or "dimension engineering" in text):
            continue

        stable = by_path.get(device) or by_id.get(device) or device
        priority = 0 if device in by_path else 1 if device in by_id else 2
        candidates.append((priority, stable))

    ordered = []
    seen = set()
    for _, stable in sorted(candidates, key=lambda item: (item[0], item[1])):
        if stable in seen:
            continue
        ordered.append(stable)
        seen.add(stable)

    return {
        "left": ordered[0] if len(ordered) > 0 else None,
        "right": ordered[1] if len(ordered) > 1 else None,
    }


def _detect_realsense_devices():
    now = time.monotonic()
    if now - _REALSENSE_CACHE["ts"] < 3.0:
        return dict(_REALSENSE_CACHE["value"])

    # Keep dashboard rendering safe: RealSense enumeration has hung inside the
    # Streamlit process on the Jetson, so prefer a short-lived subprocess.
    result = _detect_realsense_via_system_python()

    # Fall back to an in-process import only off-Jetson, where it is less risky.
    if not result.get("driver_ok") and not _on_jetson():
        rs = _load_realsense_module()
        result = {
            "driver_ok": rs is not None,
            "devices": [],
            "tracking_connected": False,
            "front_connected": False,
            "rear_connected": False,
        }
        if rs is not None:
            try:
                ctx = rs.context()
                for dev in ctx.query_devices():
                    name = dev.get_info(rs.camera_info.name)
                    serial = dev.get_info(rs.camera_info.serial_number)
                    result["devices"].append({"name": name, "serial": serial})

                    upper_name = name.upper()
                    if serial == T265_SERIAL or "T265" in upper_name or "TRACKING" in upper_name:
                        result["tracking_connected"] = True
                    if serial == FRONT_D435_SERIAL:
                        result["front_connected"] = True
                    if serial == REAR_D435_SERIAL:
                        result["rear_connected"] = True
            except Exception:
                pass

    _REALSENSE_CACHE["ts"] = now
    _REALSENSE_CACHE["value"] = dict(result)
    return dict(result)


def _detect_arduino():
    serial_ok = _import_available("serial")
    if not serial_ok:
        return {"driver_ok": False, "connected": False, "path": None}

    try:
        import serial.tools.list_ports

        for port in serial.tools.list_ports.comports():
            vid = None if port.vid is None else f"{port.vid:04x}"
            pid = None if port.pid is None else f"{port.pid:04x}"
            if vid == ARDUINO_VID and pid == ARDUINO_PID:
                return {"driver_ok": True, "connected": True, "path": port.device}
    except Exception:
        pass

    preferred = _first_existing_path(ARDUINO_FALLBACK_PORTS)
    if preferred:
        return {"driver_ok": True, "connected": True, "path": preferred}

    return {"driver_ok": True, "connected": False, "path": None}


def _status_connected(connected: bool, driver_ok: bool, on_jetson: bool) -> str:
    if connected:
        return "CONNECTED"
    if driver_ok:
        return "NO DEVICE" if on_jetson else "NO DEVICE (Off Jetson)"
    return "CHECKER MISSING"


def check_hardware_status(root_path: Path):
    hw_report = []
    hw_config_path = root_path / "lunar" / "hardware.toml"
    on_jetson = _on_jetson()

    if not hw_config_path.exists():
        st.error(f"Config not found at {hw_config_path}")
        return []

    with open(hw_config_path, "rb") as f:
        hw_data = tomli.load(f)

    realsense = _detect_realsense_devices()
    drive_ports = _discover_drive_ports()

    if "vision" in hw_data:
        for v_name, v_cfg in hw_data["vision"].items():
            model = v_cfg.get("model", v_name)
            if v_name == "tracking_camera":
                connected = realsense["tracking_connected"]
                status = _status_connected(connected, realsense["driver_ok"], on_jetson)
                detail = T265_SERIAL if connected else "T265 not detected"
            elif v_name == "rgb_camera":
                connected = realsense["front_connected"]
                status = _status_connected(connected, realsense["driver_ok"], on_jetson)
                detail = FRONT_D435_SERIAL if connected else "Front D435 RGB not detected"
            elif v_name == "rear_camera":
                connected = realsense["rear_connected"]
                status = _status_connected(connected, realsense["driver_ok"], on_jetson)
                detail = REAR_D435_SERIAL if connected else "Rear D435 RGB not detected"
            else:
                lib = v_cfg.get("driver_lib")
                driver_ok = _import_available(lib) if lib else False
                status = "DRIVER OK" if driver_ok else "DRIVER MISSING"
                detail = lib or "Unknown driver"

            hw_report.append(
                {
                    "Category": "Vision",
                    "Name": v_name,
                    "Model": model,
                    "Status": status,
                    "Detail": detail,
                }
            )

    if "actuation" in hw_data:
        if "drive_train" in hw_data["actuation"]:
            ctrl = hw_data["actuation"]["drive_train"].get("controller", "Sabertooth")
            for side in ("left", "right"):
                found_path = drive_ports.get(side) or _first_existing_path(DRIVE_PORTS[side])
                hw_report.append(
                    {
                        "Category": "Actuation",
                        "Name": f"Motor ({side})",
                        "Model": ctrl,
                        "Status": "CONNECTED" if found_path else ("NO DEVICE" if on_jetson else "NO DEVICE (Off Jetson)"),
                        "Detail": found_path or ", ".join(DRIVE_PORTS[side]),
                    }
                )

        if "mining_mechanism" in hw_data["actuation"]:
            mm = hw_data["actuation"]["mining_mechanism"]
            if "spin" in mm:
                ctrl = mm["spin"].get("controller", "Mining spin")
                found_path = _first_existing_path(MINING_SPIN_PORTS)
                hw_report.append(
                    {
                        "Category": "Actuation",
                        "Name": "Mining (spin)",
                        "Model": ctrl,
                        "Status": "CONNECTED" if found_path else ("NO DEVICE" if on_jetson else "NO DEVICE (Off Jetson)"),
                        "Detail": found_path or ", ".join(MINING_SPIN_PORTS),
                    }
                )
            if "linear" in mm:
                ctrl = mm["linear"].get("controller", "Mining linear")
                hw_report.append(
                    {
                        "Category": "Actuation",
                        "Name": "Mining (linear)",
                        "Model": ctrl,
                        "Status": "GPIO CAPABLE" if on_jetson else "OFF JETSON",
                        "Detail": "Jetson GPIO path",
                    }
                )

    if "microcontrollers" in hw_data:
        for mc_name, mc_cfg in hw_data["microcontrollers"].items():
            model = mc_cfg.get("model", mc_name)
            if mc_name == "arduino":
                detected = _detect_arduino()
                status = _status_connected(detected["connected"], detected["driver_ok"], on_jetson)
                detail = detected["path"] or "Arduino not detected"
            else:
                dev = mc_cfg.get("device_path")
                exists = Path(dev).exists() if dev else False
                status = "CONNECTED" if exists else ("NO DEVICE" if on_jetson else "NO DEVICE (Off Jetson)")
                detail = dev or "Unknown path"

            hw_report.append(
                {
                    "Category": "MCU",
                    "Name": mc_name,
                    "Model": model,
                    "Status": status,
                    "Detail": detail,
                }
            )

    return hw_report


def render_hardware_panel(root_path):
    st.subheader("Hardware Inventory")

    hw_config_path = root_path / "lunar" / "hardware.toml"
    if not hw_config_path.exists():
        st.error(f"Config not found at {hw_config_path}")
        return

    with open(hw_config_path, "rb") as f:
        hw_data = tomli.load(f)

    st.markdown("### Status Summary")
    report = check_hardware_status(root_path)
    if report:
        import pandas as pd

        df = pd.DataFrame(report)
        preferred_columns = ["Category", "Name", "Model", "Status", "Detail"]
        df = df[[col for col in preferred_columns if col in df.columns]]

        def color_status(val):
            color = "red"
            if val in ["CONNECTED", "GPIO CAPABLE", "DRIVER OK"]:
                color = "green"
            elif val in ["NO DEVICE", "NO DEVICE (Off Jetson)", "OFF JETSON"]:
                color = "orange"
            return f"color: {color}"

        styler = df.style
        if hasattr(styler, "map"):
            styler = styler.map(color_status, subset=["Status"])
        else:
            styler = styler.applymap(color_status, subset=["Status"])
        st.dataframe(styler, use_container_width=True)

    st.caption(
        "Status meanings: CONNECTED means the device was detected now. "
        "NO DEVICE means the checker ran but no matching hardware was found. "
        "GPIO CAPABLE means this Jetson can use that GPIO control path, not that an actuator was physically verified. "
        "CHECKER MISSING means the dashboard environment is missing the Python package needed to probe that device."
    )

    st.markdown("### Detailed Specifications")

    tabs = st.tabs(["Vision", "Sensors", "Actuation", "MCU", "System", "Raw TOML"])

    with tabs[0]:
        if "vision" in hw_data:
            for name, cfg in hw_data["vision"].items():
                st.write(f"**{name.replace('_', ' ').title()}**")
                st.json(cfg)

    with tabs[1]:
        if "sensors" in hw_data:
            for name, cfg in hw_data["sensors"].items():
                st.write(f"**{name.replace('_', ' ').title()}**")
                st.json(cfg)

    with tabs[2]:
        if "actuation" in hw_data:
            for name, cfg in hw_data["actuation"].items():
                st.write(f"**{name.replace('_', ' ').title()}**")
                st.json(cfg)

    with tabs[3]:
        if "microcontrollers" in hw_data:
            for name, cfg in hw_data["microcontrollers"].items():
                st.write(f"**{name.replace('_', ' ').title()}**")
                st.json(cfg)

    with tabs[4]:
        if "system" in hw_data:
            st.json(hw_data["system"])

    with tabs[5]:
        st.code(hw_config_path.read_text(), language="toml")
