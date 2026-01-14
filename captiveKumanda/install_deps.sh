#!/bin/bash
# Install dependencies for the captive portal server
# Run with: sudo ./install_deps.sh

echo "Installing Python dependencies for Gaming Kiosk Server..."
echo "==========================================================="

# Install system packages (recommended approach)
echo ""
echo "[1/2] Installing Flask via apt..."
apt-get update -qq
apt-get install -y python3-flask python3-psutil

# Install mysql-connector-python via pip (not available in apt)
echo ""
echo "[2/2] Installing MySQL connector..."
pip3 install mysql-connector-python==8.2.0 --break-system-packages

echo ""
echo "✓ All dependencies installed successfully!"
echo ""
echo "You can now run the captive portal with:"
echo "  sudo ./start.sh"
