#!/usr/bin/env bash
# Autoware simulation environment bootstrap script.
# Run once before first use: bash scripts/setup.sh

set -euo pipefail

AUTOWARE_MAP_DIR="$(pwd)/maps"

# ---------- helpers ----------
info()  { echo "[INFO]  $*"; }
warn()  { echo "[WARN]  $*" >&2; }
abort() { echo "[ERROR] $*" >&2; exit 1; }

check_deps() {
    info "Checking dependencies..."
    for cmd in docker curl; do
        command -v "$cmd" &>/dev/null || abort "$cmd is not installed."
    done

    # Docker GPU support
    if docker run --rm --gpus all nvidia/cuda:12.0-base-ubuntu22.04 nvidia-smi &>/dev/null; then
        info "NVIDIA GPU detected and accessible."
    else
        warn "NVIDIA GPU not detected. Simulation will run on CPU (slow)."
    fi
}

pull_autoware_image() {
    info "Pulling latest Autoware Docker image..."
    docker pull ghcr.io/autowarefoundation/autoware:latest-cuda
}

download_sample_map() {
    local map_dir="$AUTOWARE_MAP_DIR/nishishinjuku_autoware_map"
    if [[ -d "$map_dir" ]]; then
        info "Sample map already exists at $map_dir, skipping."
        return
    fi

    info "Downloading Nishi-Shinjuku sample map (~70 MB)..."
    mkdir -p "$AUTOWARE_MAP_DIR"

    # Official sample map distributed by Autoware Foundation
    local url="https://github.com/autowarefoundation/sample_data/raw/main/sample-map-nishishinjuku.zip"
    curl -L --retry 3 -o /tmp/sample_map.zip "$url" \
        || abort "Map download failed. Check network connectivity."

    unzip -q /tmp/sample_map.zip -d "$AUTOWARE_MAP_DIR"
    rm /tmp/sample_map.zip
    info "Map saved to $map_dir"
}

download_sample_rosbag() {
    local bag_dir="$AUTOWARE_MAP_DIR/rosbag"
    if [[ -d "$bag_dir" ]]; then
        info "Sample rosbag already exists, skipping."
        return
    fi

    info "Downloading sample rosbag (~500 MB, requires gdown)..."
    if ! command -v gdown &>/dev/null; then
        pip3 install --quiet gdown || abort "pip3 not found. Install Python 3 first."
    fi

    mkdir -p "$bag_dir"
    # Sample rosbag from Autoware Foundation Google Drive
    gdown --fuzzy "https://drive.google.com/file/d/1VnwJx9tI3kI_cTCzwTvMnH4oJfTiVCSD" \
        -O "$bag_dir/sample.db3" \
        || warn "Rosbag download failed. Manually place a .db3 file in $bag_dir"
}

allow_xhost() {
    info "Allowing X11 connections from Docker..."
    xhost +local:docker 2>/dev/null || warn "xhost not available (headless environment)."
}

main() {
    info "=== Autoware Simulation Setup ==="
    check_deps
    pull_autoware_image
    download_sample_map
    download_sample_rosbag
    allow_xhost
    info "=== Setup complete! ==="
    echo ""
    echo "Next steps:"
    echo "  Planning Simulator : bash scripts/planning_simulator.sh"
    echo "  Rosbag Replay      : bash scripts/rosbag_replay.sh"
    echo "  AWSIM              : bash scripts/awsim.sh   (download binary first)"
}

main "$@"
