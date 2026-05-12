# upmoon25-auto Unified CLI Journal

This journal documents the architectural evolution of the `upmoon25-auto` development environment and the `lunar` Unified CLI.

## Vision
To transform a fragmented ROS 2 workspace into a professional, containerized "Command Center" where a single entry point manages building, simulation, diagnostics, and remote visualization.

---

## Architectural Milestones

### 1. Environment Isolation (Docker)
- **Achievement**: Created a standardized `Dockerfile` based on ROS Humble.
- **Problem Fixed**: Resolved binary incompatibilities between `numpy` and `scipy` (pinned `numpy<2.0.0`) and ensured consistent dependencies for all developers.
- **Networking**: Configured `network_mode: host` and eventually migrated to an isolated `ROS_DOMAIN_ID=25` to prevent ghost nodes and cross-talk on shared networks.

### 2. The Unified CLI (`lunar`)
- **Achievement**: Developed a `typer`-based CLI tool that abstracts complex ROS/Gazebo commands.
- **Features**:
    - **`lunar build`**: Orchestrates sequential builds of interfaces, packages, and custom C++ Gazebo plugins. Automatically handles environment sourcing.
    - **`lunar sim`**: Launches a robust background simulation.
    - **`lunar check`**: A unified auditor that validates the environment, background processes, ROS nodes, and the TF coordinate tree.
    - **`lunar logs/kill`**: Streamlined process management and diagnostic access.

### 3. Headless Stability (Xvfb & GzServer)
- **Problem**: Gazebo Classic crashes in headless Docker environments when rendering camera/depth sensors without a display.
- **Solution**: 
    - Integrated a managed `Xvfb` (Virtual Framebuffer) session into the CLI.
    - Decoupled `gzserver` from ROS launch files to improve signal handling and stability.
    - Optimized the startup sequence (Xvfb -> GzServer -> ROS Nodes -> Bridge).

### 4. Data Integrity & Visualization
- **Achievement**: Integrated Foxglove Bridge for remote web-based visualization.
- **Coordinate Tree**: Resolved "Unconnected Tree" errors by:
    - Standardizing `static_transform_publisher` arguments for ROS 2 Humble.
    - Adding static fallback transforms for wheel links to ensure high-fidelity rendering in Foxglove even when the robot is stationary.
    - Correcting parent/child link naming conventions in the URDF and Gazebo plugins.

---

## Current System State
As of Feb 5, 2026, the system passes a "Full Green" Audit:
- ✅ **Environment**: ROS 2, Gazebo, and Xvfb are healthy.
- ✅ **Processes**: GzServer, Foxglove Bridge, and Xvfb run reliably in the background.
- ✅ **Network**: Isolated on Domain 25 with no duplicate nodes.
- ✅ **Transforms**: Full connectivity from `map` -> `odom` -> `base_link` -> `wheels/sensors`.

## Developer Workflow
```bash
make build    # Setup environment
make install  # Setup CLI
make sim      # Start robot
make check    # Verify health
make logs     # Watch output
```

---

## Consolidation Roadmap (Post-Feb 5, 2026)

Based on the latest project audit, the following opportunities have been identified to achieve 100% unification under the `lunar` CLI:

### 1. Host-Side "Transparent" Wrapper
- **Goal**: Eliminate the need to prefix commands with `docker exec`.
- **Implementation**: Create a host-side `./lunar` script that detects the environment and forwards calls into the `upmoon25_ros` container automatically.

### 2. Legacy Script Migration (The "Cleanup")
- **Goal**: Deprecate fragmented Bash scripts in the project root.
- **Targets**:
    - `BUILD.bash` → `lunar build` (already in progress)
    - `INSTALL.bash` → `lunar install`
    - `RUN_LAPTOP_RC.bash` → `lunar run rc`
    - `RUN_ROBOT.bash` → `lunar run robot`
    - `MAX_RUN.sh` → `lunar run max`

### 3. Integrated Firmware Management
- **Goal**: Manage the Arduino hardware lifecycle without "Black Box" binaries.
- **Implementation**:
    - Reconstruct Arduino source code (`ServoTest.ino`) from reversed protocols.
    - Add `lunar firmware compile/flash` using `arduino-cli`.
- **Status**: Source code reconstructed and stored in `firmware/arduino/`.

### 4. Quality Assurance (QA) Automation
- **Goal**: Moving from manual checks to automated verification.
- **Targets**:
    - `lunar lint`: (DONE) Integrates `ruff` and `ty check`.
    - `lunar test --unit`: Automated `colcon test` execution.
    - `lunar test --sim`: Functional movement verification (Smoke Test) in a headless sim.

### 5. Map & Data Management
- **Goal**: Standardize the collection of simulation and real-world data.
- **Implementation**:
    - `lunar data save-map [name]`: Trigger map-saver nodes.
    - `lunar data record`: Record rosbags of critical topics.

### 6. Visualizer (Foxglove) Orchestration
- **Goal**: Instant dashboard setup for all users.
- **Implementation**: `lunar layout export` to generate/inject pre-configured Foxglove JSON layouts with correct frames and topic layers.

### 7. Hardware Doctor (Peripheral DRC)
- **Goal**: Verify physical readiness before deployment.
- **Implementation**: (DONE) Integrated `hardware.toml` auditing into `lunar check`. Displays full configuration details and detects missing peripherals with Jetson-awareness (Not a Jetson mode).

