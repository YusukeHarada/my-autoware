#!/usr/bin/env bash
# Launch Autoware connected to the AWSIM digital twin simulator.
# AWSIM runs as a separate Unity binary outside Docker.
#
# Prerequisites:
#   1. Download AWSIM binary: bash scripts/download_awsim.sh
#   2. Run this script in one terminal
#   3. Start the AWSIM binary in another terminal

set -euo pipefail

AWSIM_MAP_PATH="$(pwd)/maps/awsim_labs_map"

[[ -d "$AWSIM_MAP_PATH" ]] || {
    echo "[ERROR] AWSIM map not found at $AWSIM_MAP_PATH"
    echo "        Run: bash scripts/download_awsim.sh"
    exit 1
}

xhost +local:docker 2>/dev/null || true

echo "[INFO] Starting Autoware (AWSIM mode)..."
echo "       Make sure the AWSIM binary is running separately."
echo "       AWSIM and Autoware communicate over localhost UDP."
echo ""

docker compose up awsim_simulator
