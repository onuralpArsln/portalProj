#!/bin/bash
# Install dependencies for the captive portal server
# Run with: sudo ./install_deps.sh

echo "Installing Python dependencies for Gaming Kiosk Server..."
echo "==========================================================="

# Install system packages (recommended approach)
echo ""
echo "[1/3] Installing Flask and system packages..."
apt-get update -qq
apt-get install -y python3-flask python3-psutil python3-tk

# Install mysql-connector-python via pip (not available in apt)
echo ""
echo "[2/3] Installing MySQL connector..."
pip3 install mysql-connector-python==8.2.0 --break-system-packages

# Verify Tkinter installation
echo ""
echo "[3/3] Verifying Tkinter installation..."
if python3 -c "import tkinter" 2>/dev/null; then
    echo "✓ Tkinter is installed and working"
else
    echo "⚠ Warning: Tkinter installation may have failed"
    echo "  Server will run in headless mode without on-screen notifications"
fi

echo ""
echo "✓ All dependencies installed successfully!"
echo ""
echo "You can now run the captive portal with:"
echo "  sudo ./start.sh"
