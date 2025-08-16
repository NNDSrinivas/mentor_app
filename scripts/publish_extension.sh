#!/usr/bin/env bash
# Package the browser extension for upload
set -e
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
EXT_DIR="$ROOT_DIR/browser_extension"
OUT_DIR="$ROOT_DIR/dist"
mkdir -p "$OUT_DIR"
ZIP_FILE="$OUT_DIR/browser_extension.zip"
rm -f "$ZIP_FILE"
(
  cd "$EXT_DIR"
  zip -r "$ZIP_FILE" . -x "node_modules/*"
)
echo "Extension packaged at $ZIP_FILE"
