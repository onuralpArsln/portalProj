#!/bin/bash
#####################################################
#  Kumanda Master System - Installation Script      #
#####################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║       🎮 KUMANDA MASTER SYSTEM - INSTALLER 🎮            ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}❌ This script must be run as root (use sudo)${NC}" 
   exit 1
fi

echo -e "${YELLOW}📦 Installing system dependencies...${NC}"

# Update package list
apt update

# Install required packages
apt install -y socat hostapd dnsmasq python3 python3-pip x11-xserver-utils

echo -e "${YELLOW}📦 Installing Python dependencies...${NC}"

# Install Python packages
pip3 install pyserial mysql-connector-python cryptography psutil --break-system-packages 2>/dev/null || \
pip3 install pyserial mysql-connector-python cryptography psutil

echo -e "${GREEN}✅ Installation complete!${NC}"
echo ""
echo -e "${BLUE}To run the system:${NC}"
echo "  1. cd $(pwd)"
echo "  2. xhost +local:root"
echo "  3. sudo python3 master.py"
echo ""
echo -e "${YELLOW}Note: Make sure to edit hostapd.conf if your WiFi interface is different from wlp5s0${NC}"
