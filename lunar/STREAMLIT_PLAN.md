# Streamlit Integration Plan: "Lunar Mission Control"

## 1. Executive Summary
This document outlines the architecture for integrating a **Streamlit-based Dashboard** directly into the `lunar` CLI. The goal is to provide a "Cockpit" interface for the `upmoon25-auto` robot that serves as a high-level Human-Robot Interface (HRI), complementing the low-level spatial debugging of RViz.

**Target User:** Robot Operator / Pilot
**Access:** Browser-based (runs on Host, connects to Container via port forwarding)
**Command:** `lunar dashboard`

---

## 2. Directory Structure
We will treat the dashboard as a sub-module of the CLI itself, ensuring it has access to the same configuration logic (`hardware.toml`, `config.py`) as the rest of the tools.

```text
lunar/
└── src/
    └── lunar/
        ├── cli.py             # Entry point (adds 'dashboard' command)
        ├── dashboard/         # NEW MODULE
        │   ├── __init__.py
        │   ├── app.py         # Main Streamlit Entry Point
        │   ├── layout.py      # UI Components (Sidebar, Header, Grid)
        │   ├── state.py       # ROS 2 State Management (Thread-safe)
        │   └── components/
        │       ├── hardware.py    # Hardware Doctor Widget
        │       ├── telemetry.py   # Odom/Vel HUD
        │       ├── mining.py      # Mining/Actuator Controls
        │       └── vision.py      # Camera Feeds & Tag Logs
        └── ...
```

---

## 3. Data Architecture (The "ROS 2 Bridge")

Streamlit is strictly synchronous (script re-runs top-to-bottom on interaction), while ROS 2 is asynchronous (callbacks). Bridging them requires a **De-coupled State Store**.

### The "Sidecar" Thread Pattern
1.  **Background Thread:** Upon launching `lunar dashboard`, a background Python thread starts a `rclpy` Node (`DashboardListener`).
2.  **Shared Memory:** This node subscribes to relevant topics (`/odom`, `/sensor/ir`, `/joint_states`) and updates a thread-safe `GlobalState` object (Python Dictionary or Dataclass).
3.  **Streamlit Loop:** The Streamlit script reads from this `GlobalState` at 10-20Hz (using `st.experimental_rerun` or periodic refresh) to update the UI without blocking the ROS callbacks.

**Key Topics to Monitor:**
- `/odom` (Position/Velocity)
- `/joint_states` (Arm/Camera Servo positions)
- `/sensor/ir` (Arduino Sensor Data)
- `/diagnostics` (Hardware Health)
- `/camera/rgb/image_raw` (Video Feed - heavily downsampled for web)

---

## 4. Feature Specification

### A. The "Command Center" (Home Tab)
- **Status Banner:** Large colored banner indicating System Status (Green/Red) derived from `lunar check` logic.
- **HUD:** 
    - Big Text metrics for **X, Y, Z** position.
    - Speedometer gauges for Linear (m/s) and Angular (rad/s) velocity.
- **Mission Log:** A scrolling text box of the last 10 log messages (`/rosout` WARN+).

### B. The "Hardware Doctor" (Health Tab)
- **Visual Inventory:** A grid view of `hardware.toml` items.
    - **Row:** Device Name | Status (Connected/Missing) | Port | Last Seen
    - **Logic:** Reuses the exact extraction logic from `lunar check` but renders it as a `st.dataframe` or colored cards.
- **Real-Time Graphs:**
    - Line chart of **Battery Voltage** (if available).
    - Line chart of **CPU/RAM Usage** (via `psutil`).

### C. Mining Ops (Payload Tab)
- **Actuator Controls:**
    - Slider for **Camera Height** (publishes to `/cmd/camera_height`).
    - Slider for **Bucket Extension** (publishes to `/cmd/bucket_pos`).
- **Feedback:**
    - Gauge for **Mining Spin RPM**.
    - Toggle Switch for **Conveyor Belt**.

### D. Settings & Config
- **TOML Editor:** A text area or form to safely edit `hardware.toml` parameters (e.g., changing a Serial Port from `/dev/ttyACM0` to `/dev/ttyUSB0`) and save to disk.
- **Sim/Real Toggle:** A switch to globally set the environment mode in `lunar` config.

---

## 5. Implementation Roadmap

### Phase 1: scaffolding
- Create `lunar/src/lunar/dashboard/` structure.
- Implement `lunar dashboard` command in `cli.py` that launches `streamlit run src/lunar/dashboard/app.py`.
- Verify `streamlit` dependency in `pyproject.toml`.

### Phase 2: The Data Bridge
- Implement the `DashboardListener` ROS node.
- Create the thread-safe `state.py` store.
- specific prototype: Subscribe to `/odom` and display live X/Y coordinates in Streamlit.

### Phase 3: Hardware Integration
- Import `hardware.toml` parser from `cli.py`.
- Render the "Hardware Doctor" grid in Streamlit.

### Phase 4: Action & Control
- Add "Publishing" capability to the Dashboard Node (Publisher for `/cmd/*` topics).
- Wire up the Sliders and Buttons to publish messages.

---

## 6. Dependencies
- `streamlit`: The UI framework.
- `pandas`: For nice data tables (Hardware list).
- `altair` or `plotly`: For beautiful, interactive graphs.
- `watchdog`: (Optional) To auto-reload if config changes.

## 7. Execution Command
```bash
# Host-side usage
lunar dashboard

# Under the hood
streamlit run lunar/src/lunar/dashboard/app.py --server.port 8501
```
