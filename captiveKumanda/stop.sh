#!/bin/bash

# Captive Portal Hotspot - Stop Script
# This script cleanly stops the captive portal and restores normal WiFi

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
INTERFACE="wlan0"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Error: This script must be run as root (use sudo)${NC}"
   exit 1
fi

echo -e "${GREEN}=== Stopping Captive Portal Hotspot ===${NC}\n"

# Step 1: Stop Python web server
echo -e "${YELLOW}[1/6]${NC} Stopping web server..."
if [ -f /tmp/portal-server.pid ]; then
    PID=$(cat /tmp/portal-server.pid)
    if kill -0 $PID 2>/dev/null; then
        kill $PID
        echo "  ✓ Web server stopped"
    else
        echo "  ℹ Web server not running"
    fi
    rm -f /tmp/portal-server.pid
else
    echo "  ℹ No PID file found"
fi

# Also kill any remaining server.py processes
pkill -f "python3 server.py" 2>/dev/null || true

# Step 2: Stop dnsmasq
echo -e "${YELLOW}[2/6]${NC} Stopping dnsmasq..."
if pgrep -x "dnsmasq" > /dev/null; then
    killall dnsmasq
    echo "  ✓ dnsmasq stopped"
else
    echo "  ℹ dnsmasq not running"
fi

# Step 3: Stop hostapd
echo -e "${YELLOW}[3/6]${NC} Stopping hostapd..."
if pgrep -x "hostapd" > /dev/null; then
    killall hostapd
    echo "  ✓ hostapd stopped"
else
    echo "  ℹ hostapd not running"
fi

# Step 4: Clear iptables rules
echo -e "${YELLOW}[4/6]${NC} Clearing iptables rules..."
iptables -t nat -F
iptables -t mangle -F
iptables -F
echo "  ✓ iptables cleared"

# Step 5: Bring down interface and clear IP
echo -e "${YELLOW}[5/6]${NC} Resetting interface $INTERFACE..."
ip addr flush dev $INTERFACE
ip link set $INTERFACE down
sleep 1

# Step 6: Restore NetworkManager management
echo -e "${YELLOW}[6/6]${NC} Restoring NetworkManager management..."
nmcli device set $INTERFACE managed yes
sleep 1

# Restart NetworkManager to ensure clean state
echo -e "${YELLOW}     ${NC} Restarting NetworkManager..."
systemctl restart NetworkManager
sleep 2

echo -e "\n${GREEN}✓ Captive Portal stopped successfully!${NC}\n"
echo -e "WiFi interface $INTERFACE is now managed by NetworkManager."
echo -e "You can connect to regular WiFi networks again.\n"

# Clean up log files if they exist
if [ -f /tmp/hostapd.log ] || [ -f /tmp/dnsmasq.log ] || [ -f /tmp/portal-server.log ]; then
    echo -e "Log files preserved:"
    [ -f /tmp/hostapd.log ] && echo "  - /tmp/hostapd.log"
    [ -f /tmp/dnsmasq.log ] && echo "  - /tmp/dnsmasq.log"
    [ -f /tmp/portal-server.log ] && echo "  - /tmp/portal-server.log"
    echo -e "\nTo remove logs: ${YELLOW}rm /tmp/hostapd.log /tmp/dnsmasq.log /tmp/portal-server.log${NC}\n"
fi
