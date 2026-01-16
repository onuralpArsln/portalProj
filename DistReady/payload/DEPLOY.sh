#!/bin/bash

# Quick Deployment Script
# Automates the entire deployment process

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Captive Portal - Quick Deploy${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Error: Must run as root (sudo)${NC}"
   exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Step 1: Install dependencies
echo -e "${YELLOW}[1/5]${NC} Installing dependencies and generating configs..."
echo -e "${BLUE}(This may take a few minutes)${NC}\n"
./setup/install_offline.sh

# Step 2: Ask about terminal lock
echo -e "\n${YELLOW}[2/5]${NC} Terminal password lock installation"
echo -n "Install terminal lock? (y/N): "
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    cd lock
    ./deploy_terminal_lock.sh
    cd ..
    echo -e "${GREEN}✓${NC} Terminal lock installed (password: 131619)\n"
else
    echo -e "${YELLOW}Skipped${NC}\n"
fi

# Step 3: Deploy to production
echo -e "${YELLOW}[3/5]${NC} Deploying to /opt/captive_portal..."
mkdir -p /opt/captive_portal
cp captive_portal /opt/captive_portal/
cp config.sh /opt/captive_portal/
cp hostapd.conf /opt/captive_portal/
cp dnsmasq.conf /opt/captive_portal/
cp security/dlI /opt/captive_portal/
echo -e "${GREEN}✓${NC} Files deployed\n"

# Step 4: Ask about systemd service
echo -e "${YELLOW}[4/5]${NC} Systemd service installation"
echo -n "Enable auto-start on boot? (y/N): "
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    cp captive_portal.service /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable captive_portal
    echo -e "${GREEN}✓${NC} Service enabled (auto-start on boot)\n"
else
    echo -e "${YELLOW}Skipped${NC}\n"
fi

# Step 5: Cleanup
echo -e "${YELLOW}[5/5]${NC} Cleanup"
echo -n "Delete deployment folders (setup, lock, security)? (y/N): "
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    rm -rf setup/ lock/ security/
    echo -e "${GREEN}✓${NC} Cleanup complete\n"
else
    echo -e "${YELLOW}Skipped${NC}\n"
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✓ Deployment Complete!${NC}"
echo -e "${BLUE}========================================${NC}\n"

echo -e "Installation path: ${YELLOW}/opt/captive_portal/${NC}\n"

echo -e "${CYAN}To start the captive portal:${NC}"
echo -e "  ${YELLOW}cd /opt/captive_portal${NC}"
echo -e "  ${YELLOW}sudo ./captive_portal${NC}\n"

echo -e "${CYAN}Or use systemd service:${NC}"
echo -e "  ${YELLOW}sudo systemctl start captive_portal${NC}"
echo -e "  ${YELLOW}sudo systemctl status captive_portal${NC}\n"
