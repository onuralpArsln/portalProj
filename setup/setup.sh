#!/bin/bash

# Captive Portal Hotspot - Setup Script
# Run this script to install dependencies and verify configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}  Captive Portal Hotspot Setup${NC}"
echo -e "${BLUE}=====================================${NC}\n"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Error: This script must be run as root (use sudo)${NC}"
   exit 1
fi

# Step 1: Detect wireless interface
echo -e "${YELLOW}[1/6]${NC} Detecting wireless interface..."
WIRELESS_IFACE=$(ip link show | grep -E "^[0-9]+: w" | awk -F': ' '{print $2}' | head -n1)

if [ -z "$WIRELESS_IFACE" ]; then
    echo -e "${RED}  ✗ No wireless interface found${NC}"
    echo "  Available interfaces:"
    ip link show | grep "^[0-9]" | awk -F': ' '{print "    - " $2}'
    exit 1
else
    echo -e "${GREEN}  ✓ Found wireless interface: $WIRELESS_IFACE${NC}"
fi

# Step 2: Check for required packages
echo -e "\n${YELLOW}[2/6]${NC} Checking required packages..."

MISSING_PACKAGES=""

# Check hostapd
if ! command -v hostapd &> /dev/null; then
    echo -e "${RED}  ✗ hostapd not found${NC}"
    MISSING_PACKAGES="$MISSING_PACKAGES hostapd"
else
    HOSTAPD_VERSION=$(hostapd -v 2>&1 | head -n1)
    echo -e "${GREEN}  ✓ hostapd installed${NC} ($HOSTAPD_VERSION)"
fi

# Check dnsmasq
if ! command -v dnsmasq &> /dev/null; then
    echo -e "${RED}  ✗ dnsmasq not found${NC}"
    MISSING_PACKAGES="$MISSING_PACKAGES dnsmasq"
else
    DNSMASQ_VERSION=$(dnsmasq -v 2>&1 | head -n1)
    echo -e "${GREEN}  ✓ dnsmasq installed${NC} ($DNSMASQ_VERSION)"
fi

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}  ✗ python3 not found${NC}"
    MISSING_PACKAGES="$MISSING_PACKAGES python3"
else
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}  ✓ python3 installed${NC} ($PYTHON_VERSION)"
fi

# Check NetworkManager
if ! command -v nmcli &> /dev/null; then
    echo -e "${YELLOW}  ! NetworkManager not found${NC}"
    echo "    Warning: stop.sh relies on NetworkManager"
else
    echo -e "${GREEN}  ✓ NetworkManager installed${NC}"
fi

# Check iptables
if ! command -v iptables &> /dev/null; then
    echo -e "${RED}  ✗ iptables not found${NC}"
    MISSING_PACKAGES="$MISSING_PACKAGES iptables"
else
    echo -e "${GREEN}  ✓ iptables installed${NC}"
fi

# Step 3: Install missing packages
if [ -n "$MISSING_PACKAGES" ]; then
    echo -e "\n${YELLOW}[3/6]${NC} Installing missing packages..."
    echo -e "  Packages to install:${MISSING_PACKAGES}"
    
    # Detect package manager
    if command -v apt-get &> /dev/null; then
        apt-get update
        apt-get install -y $MISSING_PACKAGES
    elif command -v yum &> /dev/null; then
        yum install -y $MISSING_PACKAGES
    elif command -v pacman &> /dev/null; then
        pacman -Sy --noconfirm $MISSING_PACKAGES
    else
        echo -e "${RED}  ✗ Unknown package manager${NC}"
        echo "  Please install manually: $MISSING_PACKAGES"
        exit 1
    fi
    echo -e "${GREEN}  ✓ Packages installed${NC}"
else
    echo -e "\n${YELLOW}[3/6]${NC} ${GREEN}All required packages are installed${NC}"
fi

# Step 4: Update configuration files with detected interface
echo -e "\n${YELLOW}[4/6]${NC} Updating configuration files..."

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_DIR="$PROJECT_ROOT/service"

# Update hostapd.conf
if [ -f "$SERVICE_DIR/hostapd.conf" ]; then
    if grep -q "^interface=" "$SERVICE_DIR/hostapd.conf"; then
        CURRENT_IFACE=$(grep "^interface=" "$SERVICE_DIR/hostapd.conf" | cut -d'=' -f2)
        if [ "$CURRENT_IFACE" != "$WIRELESS_IFACE" ]; then
            sed -i "s/^interface=.*/interface=$WIRELESS_IFACE/" "$SERVICE_DIR/hostapd.conf"
            echo -e "  ${GREEN}✓${NC} Updated hostapd.conf: $CURRENT_IFACE → $WIRELESS_IFACE"
        else
            echo -e "  ${GREEN}✓${NC} hostapd.conf already configured for $WIRELESS_IFACE"
        fi
    fi
else
    echo -e "${RED}  ✗ hostapd.conf not found${NC}"
fi

# Update dnsmasq.conf
if [ -f "$SERVICE_DIR/dnsmasq.conf" ]; then
    if grep -q "^interface=" "$SERVICE_DIR/dnsmasq.conf"; then
        CURRENT_IFACE=$(grep "^interface=" "$SERVICE_DIR/dnsmasq.conf" | cut -d'=' -f2)
        if [ "$CURRENT_IFACE" != "$WIRELESS_IFACE" ]; then
            sed -i "s/^interface=.*/interface=$WIRELESS_IFACE/" "$SERVICE_DIR/dnsmasq.conf"
            echo -e "  ${GREEN}✓${NC} Updated dnsmasq.conf: $CURRENT_IFACE → $WIRELESS_IFACE"
        else
            echo -e "  ${GREEN}✓${NC} dnsmasq.conf already configured for $WIRELESS_IFACE"
        fi
    fi
else
    echo -e "${RED}  ✗ dnsmasq.conf not found${NC}"
fi

# Update start.sh
if [ -f "$SERVICE_DIR/start.sh" ]; then
    if grep -q '^INTERFACE=' "$SERVICE_DIR/start.sh"; then
        sed -i "s/^INTERFACE=.*/INTERFACE=\"$WIRELESS_IFACE\"/" "$SERVICE_DIR/start.sh"
        echo -e "  ${GREEN}✓${NC} Updated start.sh interface to $WIRELESS_IFACE"
    fi
else
    echo -e "${RED}  ✗ start.sh not found${NC}"
fi

# Update stop.sh (in root)
if [ -f "$PROJECT_ROOT/stop.sh" ]; then
    if grep -q '^INTERFACE=' "$PROJECT_ROOT/stop.sh"; then
        sed -i "s/^INTERFACE=.*/INTERFACE=\"$WIRELESS_IFACE\"/" "$PROJECT_ROOT/stop.sh"
        echo -e "  ${GREEN}✓${NC} Updated stop.sh interface to $WIRELESS_IFACE"
    fi
else
    echo -e "${RED}  ✗ stop.sh not found${NC}"
fi

# Step 5: Verify required files
echo -e "\n${YELLOW}[5/6]${NC} Verifying project files..."

REQUIRED_FILES=("hostapd.conf" "dnsmasq.conf" "start.sh" "server.py" "portal.html")
MISSING_FILES=""

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$SERVICE_DIR/$file" ]; then
        echo -e "  ${GREEN}✓${NC} service/$file"
    else
        echo -e "  ${RED}✗${NC} service/$file (missing)"
        MISSING_FILES="$MISSING_FILES $file"
    fi
done

# Check stop.sh in root
if [ -f "$PROJECT_ROOT/stop.sh" ]; then
    echo -e "  ${GREEN}✓${NC} stop.sh (root)"
else
    echo -e "  ${RED}✗${NC} stop.sh (missing from root)"
    MISSING_FILES="$MISSING_FILES stop.sh"
fi

if [ -n "$MISSING_FILES" ]; then
    echo -e "\n${RED}Error: Missing required files:$MISSING_FILES${NC}"
    exit 1
fi

# Step 6: Check permissions and make scripts executable
echo -e "\n${YELLOW}[6/6]${NC} Setting script permissions..."

chmod +x "$SERVICE_DIR/start.sh"
chmod +x "$PROJECT_ROOT/stop.sh"
chmod +x "$SERVICE_DIR/server.py"

echo -e "${GREEN}  ✓ Scripts are executable${NC}"

# Summary
echo -e "\n${BLUE}=====================================${NC}"
echo -e "${GREEN}✓ Setup Complete!${NC}"
echo -e "${BLUE}=====================================${NC}\n"

echo -e "Configuration Summary:"
echo -e "  Wireless Interface: ${GREEN}$WIRELESS_IFACE${NC}"
echo -e "  SSID: ${GREEN}CaptivePortal${NC}"
echo -e "  Password: ${GREEN}portal123${NC}"
echo -e "  Gateway IP: ${GREEN}192.168.4.1${NC}"
echo -e ""
echo -e "To start the captive portal:"
echo -e "  ${YELLOW}cd service && sudo ./start.sh${NC}"
echo -e ""
echo -e "To stop the captive portal:"
echo -e "  ${YELLOW}cd .. && sudo ./stop.sh${NC}  (from project root)"
echo -e ""

# Optional: Check if hostapd/dnsmasq services are enabled
if systemctl is-enabled hostapd &> /dev/null || systemctl is-enabled dnsmasq &> /dev/null; then
    echo -e "${YELLOW}Warning:${NC} hostapd or dnsmasq system services are enabled."
    echo -e "  This may conflict with the manual startup. Consider disabling:"
    echo -e "  ${YELLOW}sudo systemctl disable hostapd dnsmasq${NC}"
    echo -e "  ${YELLOW}sudo systemctl stop hostapd dnsmasq${NC}"
fi

echo ""
