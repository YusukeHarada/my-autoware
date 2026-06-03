#!/usr/bin/env bash
# Launch Autoware Planning Simulator.
# Lets you interactively set start/goal poses and add dummy obstacles in RViz.

set -euo pipefail

MAP_PATH="$(pwd)/maps/nishishinjuku_autoware_map"

[[ -d "$MAP_PATH" ]] || {
    echo "[ERROR] Map not found at $MAP_PATH"
    echo "        Run: bash scripts/setup.sh"
    exit 1
}

xhost +local:docker 2>/dev/null || true

echo "[INFO] Starting Planning Simulator..."
echo "       In RViz:"
echo "         1. Click '2D Pose Estimate' → set initial position on map"
echo "         2. Click '2D Nav Goal'      → set destination"
echo "         3. Click 'AutowareStatePanel > Engage' to start driving"
echo "         4. Add dummy cars/pedestrians with the toolbar buttons"
echo ""

docker compose run --rm planning_simulator
