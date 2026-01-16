#!/bin/bash
# Terminal Lock Removal Script
# Run this script to DISABLE the terminal password protection

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}========================================"
echo -e "  Terminal Lock Removal"
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

echo -e "Removing terminal lock for user: $ACTUAL_USER"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCK_SCRIPT="$SCRIPT_DIR/terminal_lock.sh"

# Remove immutable flag if present
chattr -i "$LOCK_SCRIPT" 2>/dev/null || true

# Remove from .bashrc
BASHRC="$USER_HOME/.bashrc"
if [ -f "$BASHRC" ]; then
    sed -i '/terminal_lock.sh/d' "$BASHRC"
    sed -i '/Terminal password lock/d' "$BASHRC"
    echo -e "${GREEN}✓${NC} Removed from .bashrc"
fi

# Remove from .profile
PROFILE="$USER_HOME/.profile"
if [ -f "$PROFILE" ]; then
    sed -i '/terminal_lock.sh/d' "$PROFILE"
    sed -i '/Terminal password lock/d' "$PROFILE"
    echo -e "${GREEN}✓${NC} Removed from .profile"
fi

# Remove from .bash_profile
BASH_PROFILE="$USER_HOME/.bash_profile"
if [ -f "$BASH_PROFILE" ]; then
    sed -i '/terminal_lock.sh/d' "$BASH_PROFILE"
    sed -i '/Terminal password lock/d' "$BASH_PROFILE"
    echo -e "${GREEN}✓${NC} Removed from .bash_profile"
fi

echo ""
echo -e "${GREEN}========================================"
echo -e "  Terminal Lock Removed Successfully"
echo -e "========================================${NC}"
echo ""
echo -e "${YELLOW}Note:${NC} Currently open terminals will still run the lock on reload."
echo -e "New terminals will no longer require a password."
echo ""
