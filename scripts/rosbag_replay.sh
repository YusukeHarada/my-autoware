#!/usr/bin/env bash
# Replay a rosbag through Autoware's Sensing / Localization / Perception stack.
# Usage: bash scripts/rosbag_replay.sh [path/to/bag.db3]

set -euo pipefail

BAG_FILE="${1:-$(pwd)/maps/rosbag/sample.db3}"
MAP_PATH="$(pwd)/maps/nishishinjuku_autoware_map"

[[ -f "$BAG_FILE" ]] || {
    echo "[ERROR] Rosbag not found: $BAG_FILE"
    echo "        Run: bash scripts/setup.sh  (to download the sample bag)"
    echo "        Or:  bash scripts/rosbag_replay.sh /path/to/your.db3"
    exit 1
}

[[ -d "$MAP_PATH" ]] || {
    echo "[ERROR] Map not found at $MAP_PATH. Run: bash scripts/setup.sh"
    exit 1
}

xhost +local:docker 2>/dev/null || true

echo "[INFO] Starting Autoware logging simulator..."

# Start the simulator in the background
docker compose up -d rosbag_replay

echo "[INFO] Waiting for Autoware to initialize (15s)..."
sleep 15

echo "[INFO] Playing rosbag: $BAG_FILE"
docker compose exec rosbag_replay bash -c "
    source /opt/autoware/setup.bash &&
    ros2 bag play '$BAG_FILE' --clock 200 -r 1.0
"
