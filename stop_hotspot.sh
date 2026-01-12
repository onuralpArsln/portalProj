#!/bin/bash

#####################################################
#  WiFi Hotspot with Captive Portal - Stop Script   #
#####################################################

INTERFACE="wlp5s0"
IP_ADDR="192.168.4.1"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║        🛑  STOPPING WIFI HOTSPOT & CAPTIVE PORTAL  🛑      ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}❌ This script must be run as root (use sudo)${NC}" 
   exit 1
fi

echo -e "${YELLOW}🧹 Stopping services...${NC}"

# Kill processes
pkill -f "hostapd.*hostapd.conf" 2>/dev/null && echo -e "${GREEN}   ✓ Stopped hostapd${NC}"
pkill -f "dnsmasq.*dnsmasq.conf" 2>/dev/null && echo -e "${GREEN}   ✓ Stopped dnsmasq${NC}"
pkill -f "server.py" 2>/dev/null && echo -e "${GREEN}   ✓ Stopped web server${NC}"

echo -e "${YELLOW}🧹 Removing iptables rules...${NC}"

# Remove iptables rules
iptables -t nat -D PREROUTING -i $INTERFACE -p tcp --dport 80 -j DNAT --to-destination $IP_ADDR:80 2>/dev/null
iptables -t nat -D PREROUTING -i $INTERFACE -p tcp --dport 443 -j DNAT --to-destination $IP_ADDR:80 2>/dev/null
iptables -D FORWARD -i $INTERFACE -j ACCEPT 2>/dev/null
echo -e "${GREEN}   ✓ iptables rules removed${NC}"

echo -e "${YELLOW}🧹 Restoring network interface...${NC}"

# Restore NetworkManager control
ip link set $INTERFACE down 2>/dev/null
ip addr flush dev $INTERFACE 2>/dev/null
nmcli device set $INTERFACE managed yes 2>/dev/null

# Restart NetworkManager to restore WiFi
systemctl restart NetworkManager 2>/dev/null

echo -e "${GREEN}   ✓ Network interface restored${NC}"

echo ""
echo -e "${GREEN}✅ Hotspot stopped. Normal WiFi should be restored shortly.${NC}"
