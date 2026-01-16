#!/bin/bash
# Terminal Lock Deployment Script
# Automatically installs terminal lock system to /opt/terminal_lock/
# Run this on each new device to deploy the lock

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================"
echo -e "  Terminal Lock Deployment"
echo -e "========================================${NC}"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Error: This script must be run as root (use sudo)${NC}"
   exit 1
fi

# Get the actual user
if [ -n "$SUDO_USER" ]; then
    ACTUAL_USER="$SUDO_USER"
    USER_HOME="/home/$SUDO_USER"
else
    echo -e "${RED}Error: Could not determine actual user. Run with sudo.${NC}"
    exit 1
fi

echo -e "${YELLOW}Deploying for user: $ACTUAL_USER${NC}"
echo ""

# Define installation directory
INSTALL_DIR="/opt/terminal_lock"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if already installed
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}⚠ Terminal lock already installed at $INSTALL_DIR${NC}"
    echo -n "Reinstall? (y/N): "
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Installation cancelled.${NC}"
        exit 0
    fi
    echo ""
fi

# Verify required files exist
echo -e "${BLUE}[1/4]${NC} Verifying required files..."
REQUIRED_FILES=(
    "$SCRIPT_DIR/lock.sh"
    "$SCRIPT_DIR/unlock.sh"
    "$SCRIPT_DIR/terminal_lock.sh"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}✗ Missing required file: $file${NC}"
        exit 1
    fi
done
echo -e "${GREEN}✓${NC} All required files found"
echo ""

# Create installation directory
echo -e "${BLUE}[2/4]${NC} Creating installation directory..."
mkdir -p "$INSTALL_DIR"
echo -e "${GREEN}✓${NC} Created $INSTALL_DIR"
echo ""

# Copy files
echo -e "${BLUE}[3/4]${NC} Copying files to $INSTALL_DIR..."
cp "$SCRIPT_DIR/lock.sh" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/unlock.sh" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/terminal_lock.sh" "$INSTALL_DIR/"

# Set permissions
chmod +x "$INSTALL_DIR/lock.sh"
chmod +x "$INSTALL_DIR/unlock.sh"
chmod +x "$INSTALL_DIR/terminal_lock.sh"

echo -e "${GREEN}✓${NC} Files copied successfully"
echo ""

# Run installation
echo -e "${BLUE}[4/4]${NC} Installing terminal lock..."
echo ""
cd "$INSTALL_DIR"
./lock.sh

echo ""
echo -e "${GREEN}========================================"
echo -e "  Deployment Complete!"
echo -e "========================================${NC}"
echo ""
echo -e "${BLUE}Installation Location:${NC} $INSTALL_DIR"
echo -e "${BLUE}Password:${NC} ${YELLOW}131619${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo -e "  1. ${GREEN}Test${NC} by opening a new terminal (Ctrl+Alt+T)"
echo -e "  2. Verify password works before logging out"
echo -e "  3. To remove: ${YELLOW}sudo /opt/terminal_lock/unlock.sh${NC}"
echo ""
echo -e "${RED}⚠ IMPORTANT:${NC} Keep /opt/terminal_lock/ - do NOT delete it!"
echo ""
