#!/bin/bash
#####################################################
#  Kumanda Master System - Start Script             #
#####################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Grant X display access for GUI
xhost +local:root 2>/dev/null || true

# Run master script
cd "$SCRIPT_DIR"
sudo python3 master.py
