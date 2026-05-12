# teleop_component

Small local Streamlit component for press-and-hold teleop controls.

This bundle is intentionally static so the Jetson runtime does not need Node.

## Layout

- `build/index.html`
- `build/index.js`

## Behavior

- Sends `streamlit:setComponentValue` on press, heartbeat, and release
- Stops active holds on `blur`, `visibilitychange`, and `beforeunload`
- Uses a 100 ms heartbeat cadence to support the backend watchdog
