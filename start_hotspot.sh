#!/bin/bash

#####################################################
#  WiFi Hotspot with Captive Portal - Start Script  #
#####################################################

# Configuration
INTERFACE="wlp5s0"
IP_ADDR="192.168.4.1"
NETMASK="255.255.255.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║        🛜  STARTING WIFI HOTSPOT & CAPTIVE PORTAL  🛜      ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}❌ This script must be run as root (use sudo)${NC}" 
   exit 1
fi

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}🧹 Cleaning up...${NC}"
    
    # Kill processes
    pkill -f "hostapd.*hostapd.conf" 2>/dev/null
    pkill -f "dnsmasq.*dnsmasq.conf" 2>/dev/null
    pkill -f "server.py" 2>/dev/null
    
    # Remove iptables rules
    iptables -t nat -D PREROUTING -i $INTERFACE -p tcp --dport 80 -j DNAT --to-destination $IP_ADDR:80 2>/dev/null
    iptables -t nat -D PREROUTING -i $INTERFACE -p tcp --dport 443 -j DNAT --to-destination $IP_ADDR:80 2>/dev/null
    iptables -D FORWARD -i $INTERFACE -j ACCEPT 2>/dev/null
    
    # Restore NetworkManager control
    nmcli device set $INTERFACE managed yes 2>/dev/null
    
    # Bring interface down
    ip link set $INTERFACE down 2>/dev/null
    ip addr flush dev $INTERFACE 2>/dev/null
    
    echo -e "${GREEN}✅ Cleanup complete${NC}"
    exit 0
}

# Set trap for cleanup on exit
trap cleanup EXIT INT TERM

# Step 1: Stop NetworkManager from managing this interface
echo -e "${YELLOW}📡 Step 1: Configuring network interface...${NC}"
nmcli device set $INTERFACE managed no 2>/dev/null

# Kill any existing instances
pkill -f "hostapd.*hostapd.conf" 2>/dev/null
pkill -f "dnsmasq.*dnsmasq.conf" 2>/dev/null
pkill -f "server.py" 2>/dev/null

# Stop any existing wpa_supplicant on this interface
pkill -f "wpa_supplicant.*$INTERFACE" 2>/dev/null

sleep 1

# Step 2: Configure the interface
echo -e "${YELLOW}📡 Step 2: Setting IP address...${NC}"
ip link set $INTERFACE down
ip addr flush dev $INTERFACE
ip addr add $IP_ADDR/24 dev $INTERFACE
ip link set $INTERFACE up

sleep 1

# Verify interface is up
if ! ip addr show $INTERFACE | grep -q "$IP_ADDR"; then
    echo -e "${RED}❌ Failed to configure interface with IP $IP_ADDR${NC}"
    exit 1
fi
echo -e "${GREEN}   ✓ Interface configured with $IP_ADDR${NC}"

# Step 3: Start hostapd
echo -e "${YELLOW}📡 Step 3: Starting WiFi Access Point (hostapd)...${NC}"
hostapd "$SCRIPT_DIR/hostapd.conf" -B
sleep 2

if ! pgrep -f "hostapd.*hostapd.conf" > /dev/null; then
    echo -e "${RED}❌ Failed to start hostapd${NC}"
    exit 1
fi
echo -e "${GREEN}   ✓ WiFi AP 'CaptivePortal' is broadcasting${NC}"

# Step 4: Start dnsmasq
echo -e "${YELLOW}📡 Step 4: Starting DHCP/DNS server (dnsmasq)...${NC}"
dnsmasq -C "$SCRIPT_DIR/dnsmasq.conf"
sleep 1

if ! pgrep -f "dnsmasq.*dnsmasq.conf" > /dev/null; then
    echo -e "${RED}❌ Failed to start dnsmasq${NC}"
    exit 1
fi
echo -e "${GREEN}   ✓ DHCP/DNS server running${NC}"

# Step 5: Configure iptables for captive portal redirect
echo -e "${YELLOW}📡 Step 5: Configuring captive portal redirect...${NC}"

# Enable IP forwarding
echo 1 > /proc/sys/net/ipv4/ip_forward

# Redirect HTTP traffic to our server
iptables -t nat -A PREROUTING -i $INTERFACE -p tcp --dport 80 -j DNAT --to-destination $IP_ADDR:80

# Redirect HTTPS traffic to our server (for captive portal detection)
iptables -t nat -A PREROUTING -i $INTERFACE -p tcp --dport 443 -j DNAT --to-destination $IP_ADDR:80

# Allow forwarding on this interface
iptables -A FORWARD -i $INTERFACE -j ACCEPT

echo -e "${GREEN}   ✓ Captive portal redirect configured${NC}"

# Step 6: Start the web server
echo -e "${YELLOW}📡 Step 6: Starting captive portal web server...${NC}"
echo ""

cd "$SCRIPT_DIR"
python3 server.py
