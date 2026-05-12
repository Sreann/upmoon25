#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKETCH="${SCRIPT_DIR}/arduinoLuna.ino"
BUILD_DIR="${SCRIPT_DIR}/build"
FQBN="${ARDUINO_FQBN:-arduino:avr:uno}"

if ! command -v arduino-cli >/dev/null 2>&1; then
  echo "arduino-cli is required to compile arduinoLuna. Install it, then rerun." >&2
  exit 1
fi

arduino-cli compile \
  --fqbn "${FQBN}" \
  --output-dir "${BUILD_DIR}" \
  "${SKETCH}"

echo "Built firmware at ${BUILD_DIR}"
