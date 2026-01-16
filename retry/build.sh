#!/bin/bash
# Build script for Captive Portal

# Ensure we are in the script directory
cd "$(dirname "$0")"

echo "Building Captive Portal binary..."

# Clean old build files
rm -rf build dist captive_portal.spec

# Build the binary
# --onefile: Create a single executable
# --add-data: Include portal.html (src:dst) - on Linux/Unix use : as separator
# --name: Output binary name
# --hidden-import: Ensure all dynamic imports are caught
pyinstaller --onefile \
            --add-data "portal.html:." \
            --name "captive_portal" \
            --clean \
            launcher.py

if [ $? -eq 0 ]; then
    echo "=================================================="
    echo "Build SUCCESSFUL!"
    echo "Binary: dist/captive_portal"
    echo "=================================================="
    echo "To run:"
    echo "  sudo ./dist/captive_portal"
    echo "=================================================="
else
    echo "Build FAILED!"
    exit 1
fi
