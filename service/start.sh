#!/bin/bash

# Captive Portal Hotspot - Start Script
# This script sets up a WiFi hotspot with captive portal using hostapd and dnsmasq

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
INTERFACE="wlan0"
STATIC_IP="192.168.4.1"
NETMASK="255.255.255.0"
SERVICE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Error: This script must be run as root (use sudo)${NC}"
   exit 1
fi

echo -e "${GREEN}=== Starting Captive Portal Hotspot ===${NC}\n"

# Check if required files exist
if [ ! -f "$SERVICE_DIR/hostapd.conf" ]; then
    echo -e "${RED}Error: hostapd.conf not found${NC}"
    exit 1
fi

if [ ! -f "$SERVICE_DIR/dnsmasq.conf" ]; then
    echo -e "${RED}Error: dnsmasq.conf not found${NC}"
    exit 1
fi

if [ ! -f "$SERVICE_DIR/server.py" ]; then
    echo -e "${RED}Error: server.py not found${NC}"
    exit 1
fi

# Step 1: Stop NetworkManager management of wireless interface
echo -e "${YELLOW}[1/7]${NC} Stopping NetworkManager on $INTERFACE..."
nmcli device set $INTERFACE managed no
sleep 1

# Step 2: Bring down the interface
echo -e "${YELLOW}[2/7]${NC} Bringing down interface $INTERFACE..."
ip link set $INTERFACE down
sleep 1

# Step 3: Configure static IP
echo -e "${YELLOW}[3/7]${NC} Configuring static IP $STATIC_IP..."
ip addr flush dev $INTERFACE
ip addr add $STATIC_IP/24 dev $INTERFACE
ip link set $INTERFACE up
sleep 1

# Step 4: Start hostapd
echo -e "${YELLOW}[4/7]${NC} Starting hostapd..."
hostapd -B "$SERVICE_DIR/hostapd.conf" > /tmp/hostapd.log 2>&1
sleep 2

# Check if hostapd is running
if ! pgrep -x "hostapd" > /dev/null; then
    echo -e "${RED}Error: hostapd failed to start. Check /tmp/hostapd.log${NC}"
    # Restore interface
    nmcli device set $INTERFACE managed yes
    exit 1
fi

# Step 5: Start dnsmasq
echo -e "${YELLOW}[5/7]${NC} Starting dnsmasq..."
dnsmasq -C "$SERVICE_DIR/dnsmasq.conf" --log-facility=/tmp/dnsmasq.log
sleep 1

# Check if dnsmasq is running
if ! pgrep -x "dnsmasq" > /dev/null; then
    echo -e "${RED}Error: dnsmasq failed to start. Check /tmp/dnsmasq.log${NC}"
    # Cleanup
    killall hostapd 2>/dev/null
    nmcli device set $INTERFACE managed yes
    exit 1
fi

# Step 6: Configure iptables for captive portal
echo -e "${YELLOW}[6/7]${NC} Configuring iptables..."
# Flush existing rules for captive portal
iptables -t nat -F
iptables -t mangle -F
iptables -F

# Redirect HTTP to web server
iptables -t nat -A PREROUTING -i $INTERFACE -p tcp --dport 80 -j DNAT --to-destination $STATIC_IP:80
iptables -t nat -A PREROUTING -i $INTERFACE -p tcp --dport 443 -j DNAT --to-destination $STATIC_IP:80

# Allow traffic from/to the interface
iptables -A INPUT -i $INTERFACE -j ACCEPT
iptables -A OUTPUT -o $INTERFACE -j ACCEPT

# Step 7: Start Python web server
echo -e "${YELLOW}[7/7]${NC} Starting web server..."
cd "$SERVICE_DIR"
python3 server.py > /tmp/portal-server.log 2>&1 &
echo $! > /tmp/portal-server.pid
sleep 1

# Check if server is running
if ! kill -0 $(cat /tmp/portal-server.pid 2>/dev/null) 2>/dev/null; then
    echo -e "${RED}Error: Web server failed to start. Check /tmp/portal-server.log${NC}"
    # Cleanup
    killall dnsmasq 2>/dev/null
    killall hostapd 2>/dev/null
    iptables -t nat -F
    nmcli device set $INTERFACE managed yes
    exit 1
fi

echo -e "\n${GREEN}✓ Captive Portal Hotspot is running!${NC}\n"
echo -e "SSID: ${GREEN}CaptivePortal${NC}"
echo -e "Password: ${GREEN}portal123${NC}"
echo -e "Gateway IP: ${GREEN}$STATIC_IP${NC}"
echo -e "\nClients will be redirected to the captive portal page automatically."
echo -e "To stop the hotspot, run: ${YELLOW}sudo ./stop.sh${NC}\n"
echo -e "Logs:"
echo -e "  - hostapd: /tmp/hostapd.log"
echo -e "  - dnsmasq: /tmp/dnsmasq.log"
echo -e "  - web server: /tmp/portal-server.log"
