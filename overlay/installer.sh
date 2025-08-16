#!/usr/bin/env bash
# Build a lightweight zip installer for the overlay
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DIST_DIR="$SCRIPT_DIR/dist"
mkdir -p "$DIST_DIR"
cd "$SCRIPT_DIR"
zip -r "$DIST_DIR/mentor-overlay.zip" . -x "dist/*" "node_modules/*"
echo "Installer written to $DIST_DIR/mentor-overlay.zip"
