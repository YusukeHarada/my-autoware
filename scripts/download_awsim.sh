#!/usr/bin/env bash
# Download AWSIM Labs binary and map data for digital twin simulation.
# AWSIM requires an NVIDIA GPU (RTX 2080 or better recommended).

set -euo pipefail

MAPS_DIR="$(pwd)/maps"
AWSIM_DIR="$(pwd)/awsim"

info()  { echo "[INFO]  $*"; }
abort() { echo "[ERROR] $*" >&2; exit 1; }

command -v gdown &>/dev/null || pip3 install --quiet gdown \
    || abort "pip3 not found. Install Python 3."

# ---------- AWSIM Labs binary ----------
info "Downloading AWSIM Labs binary (~1.4 GB)..."
mkdir -p "$AWSIM_DIR"
gdown --fuzzy \
    "https://github.com/autowarefoundation/AWSIM-Labs/releases/latest/download/AWSIM_Labs_Linux.zip" \
    -O /tmp/awsim.zip \
    || abort "AWSIM download failed. Check the release page for the latest URL:
    https://github.com/autowarefoundation/AWSIM-Labs/releases"

unzip -q /tmp/awsim.zip -d "$AWSIM_DIR"
chmod +x "$AWSIM_DIR"/AWSIM_Labs.x86_64 2>/dev/null || true
rm /tmp/awsim.zip
info "AWSIM saved to $AWSIM_DIR"

# ---------- AWSIM map ----------
info "Downloading AWSIM Labs map (~200 MB)..."
mkdir -p "$MAPS_DIR/awsim_labs_map"
gdown --fuzzy \
    "https://github.com/autowarefoundation/AWSIM-Labs/releases/latest/download/awsim_labs_map.zip" \
    -O /tmp/awsim_map.zip \
    || abort "Map download failed."

unzip -q /tmp/awsim_map.zip -d "$MAPS_DIR/awsim_labs_map"
rm /tmp/awsim_map.zip
info "Map saved to $MAPS_DIR/awsim_labs_map"

echo ""
echo "=== AWSIM setup complete ==="
echo ""
echo "To run the simulation:"
echo "  Terminal 1 (Autoware): bash scripts/awsim.sh"
echo "  Terminal 2 (AWSIM)   : $AWSIM_DIR/AWSIM_Labs.x86_64"
