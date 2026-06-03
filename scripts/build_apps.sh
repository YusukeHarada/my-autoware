#!/usr/bin/env bash
# Build all custom ROS 2 packages inside the Autoware Docker container.
# Run this once after cloning to compile the apps/ workspace.
#
# Usage: bash scripts/build_apps.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "[INFO] Building custom packages inside Autoware container..."

docker run --rm \
    --network host \
    -v "$REPO_ROOT/apps:/ws/src" \
    -v "$REPO_ROOT/results:/results" \
    ghcr.io/autowarefoundation/autoware:latest-cuda \
    bash -c "
        set -e
        source /opt/autoware/setup.bash
        cd /ws
        echo '[BUILD] Installing Python deps...'
        pip install --quiet torch torchvision opencv-python-headless matplotlib
        echo '[BUILD] Running colcon build...'
        colcon build \
            --symlink-install \
            --cmake-args -DCMAKE_BUILD_TYPE=Release \
            2>&1 | tail -30
        echo '[BUILD] Done.'
        source install/setup.bash
        echo '[TEST] Verifying imports...'
        python -c 'import speed_monitor; import violation_logger; import metrics_analyzer; print(\"All packages OK\")'
    "

echo "[INFO] Build complete."
echo "       Re-run simulations to use the updated nodes."
