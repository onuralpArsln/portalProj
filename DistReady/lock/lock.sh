#!/bin/bash
# Terminal Lock Installation Script
# Run this script to enable password protection on all new terminal sessions
# Password: 131619

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================"
echo -e "  Terminal Lock Installation"
echo -e "========================================${NC}"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Error: This script must be run as root (use sudo)${NC}"
   exit 1
fi

# Get the actual user (not root)
if [ -n "$SUDO_USER" ]; then
    ACTUAL_USER="$SUDO_USER"
    USER_HOME="/home/$SUDO_USER"
else
    echo -e "${RED}Error: Could not determine actual user. Run with sudo.${NC}"
    exit 1
fi

echo -e "${YELLOW}Installing terminal lock for user: $ACTUAL_USER${NC}"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCK_SCRIPT="$SCRIPT_DIR/security/terminal_lock.sh"

# Make sure lock script exists and is executable
if [ ! -f "$LOCK_SCRIPT" ]; then
    echo -e "${RED}Error: terminal_lock.sh not found in security/${NC}"
    exit 1
fi

chmod +x "$LOCK_SCRIPT"
echo -e "${GREEN}✓${NC} Lock script prepared: $LOCK_SCRIPT"

# Install into .bashrc (for bash shells)
BASHRC="$USER_HOME/.bashrc"
LOCK_LINE="source $LOCK_SCRIPT"

if ! grep -q "terminal_lock.sh" "$BASHRC" 2>/dev/null; then
    echo "" >> "$BASHRC"
    echo "# Terminal password lock - DO NOT REMOVE" >> "$BASHRC"
    echo "$LOCK_LINE" >> "$BASHRC"
    chown "$ACTUAL_USER:$ACTUAL_USER" "$BASHRC"
    echo -e "${GREEN}✓${NC} Added to .bashrc"
else
    echo -e "${YELLOW}⚠${NC} Already installed in .bashrc"
fi

# Install into .profile (for login shells)
PROFILE="$USER_HOME/.profile"
if [ -f "$PROFILE" ]; then
    if ! grep -q "terminal_lock.sh" "$PROFILE" 2>/dev/null; then
        echo "" >> "$PROFILE"
        echo "# Terminal password lock - DO NOT REMOVE" >> "$PROFILE"
        echo "$LOCK_LINE" >> "$PROFILE"
        chown "$ACTUAL_USER:$ACTUAL_USER" "$PROFILE"
        echo -e "${GREEN}✓${NC} Added to .profile"
    else
        echo -e "${YELLOW}⚠${NC} Already installed in .profile"
    fi
fi

# Install into .bash_profile if it exists
BASH_PROFILE="$USER_HOME/.bash_profile"
if [ -f "$BASH_PROFILE" ]; then
    if ! grep -q "terminal_lock.sh" "$BASH_PROFILE" 2>/dev/null; then
        echo "" >> "$BASH_PROFILE"
        echo "# Terminal password lock - DO NOT REMOVE" >> "$BASH_PROFILE"
        echo "$LOCK_LINE" >> "$BASH_PROFILE"
        chown "$ACTUAL_USER:$ACTUAL_USER" "$BASH_PROFILE"
        echo -e "${GREEN}✓${NC} Added to .bash_profile"
    else
        echo -e "${YELLOW}⚠${NC} Already installed in .bash_profile"
    fi
fi

# Make files immutable to prevent easy removal
chattr +i "$LOCK_SCRIPT" 2>/dev/null || echo -e "${YELLOW}⚠${NC} Could not make lock script immutable"

echo ""
echo -e "${GREEN}========================================"
echo -e "  Terminal Lock Installed Successfully"
echo -e "========================================${NC}"
echo ""
echo -e "Password: ${YELLOW}131619${NC}"
echo ""
echo -e "${YELLOW}IMPORTANT:${NC}"
echo -e "  - This terminal session is ALREADY open, no password needed here"
echo -e "  - ${RED}ALL NEW${NC} terminal sessions will require the password"
echo -e "  - ${RED}3 failed attempts = Device shutdown${NC}"
echo -e "  - To unlock: Run ${YELLOW}sudo ./unlock.sh${NC}"
echo ""
echo -e "${RED}Test carefully!${NC} Open a new terminal to verify it works."
echo ""
