#!/bin/bash

# Captive Portal Hotspot - Start Script
# This script sets up a WiFi hotspot with captive portal using hostapd and dnsmasq

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Verbose logging
VERBOSE=1  # Set to 0 to disable verbose output

log_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    if [ "$VERBOSE" -eq 1 ]; then
        echo -e "${BLUE}[DEBUG]${NC} $1"
    fi
}

# Get script directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
log_debug "Project directory: $PROJECT_ROOT"

# Load configuration
CONFIG_FILE="$PROJECT_ROOT/config.sh"
if [ ! -f "$CONFIG_FILE" ]; then
    log_error "Configuration file not found: $CONFIG_FILE"
    echo -e "Please create config.sh from the template"
    exit 1
fi

# Source configuration
log_debug "Loading configuration from: $CONFIG_FILE"
source "$CONFIG_FILE"


echo -e "\n${GREEN}=== Starting Captive Portal Hotspot ===${NC}\n"

# AUTOMATIC DISPLAY PERMISSION
# We need to allow the 'root' user (us) to draw on the logged-in user's screen.
# If we were started with sudo, we know who the real user is ($SUDO_USER).
if [ -n "$SUDO_USER" ]; then
    log_info "Granting X11 display permission for root (via $SUDO_USER)..."
    # Run xhost as the normal user
    # 'xhost +local:root' allows root to connect to the X server
    sudo -u $SUDO_USER env DISPLAY=:0 xhost +local:root >/dev/null 2>&1 || true
else
    # Fallback if SUDO_USER is missing (e.g. run directly as root login)
    # This might fail if we can't find the Xauthority, but it's worth a try.
    export DISPLAY=:0
    xhost +local:root >/dev/null 2>&1 || true
fi

echo -e "${CYAN}Configuration:${NC}"
echo -e "  Interface:    ${YELLOW}$INTERFACE${NC}"
echo -e "  Static IP:    ${YELLOW}$STATIC_IP${NC}"
echo -e "  SSID:         ${YELLOW}$SSID${NC}"
echo -e "  Server Port:  ${YELLOW}$SERVER_PORT${NC}"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   log_error "This script must be run as root (use sudo)"
   exit 1
fi

# Check if required files exist
log_info "Checking required files..."
if [ ! -f "$PROJECT_ROOT/hostapd.conf" ]; then
    log_error "hostapd.conf not found in $PROJECT_ROOT"
    exit 1
fi
log_debug "✓ hostapd.conf found"

if [ ! -f "$PROJECT_ROOT/dnsmasq.conf" ]; then
    log_error "dnsmasq.conf not found in $PROJECT_ROOT"
    exit 1
fi
log_debug "✓ dnsmasq.conf found"

if [ ! -f "$PROJECT_ROOT/server.py" ]; then
    log_error "server.py not found in $PROJECT_ROOT"
    exit 1
fi
log_debug "✓ server.py found"

if [ ! -f "$PROJECT_ROOT/portal.html" ]; then
    log_error "portal.html not found in $PROJECT_ROOT"
    exit 1
fi
log_debug "✓ portal.html found"

# Step 1: Check if interface exists
echo -e "\n${YELLOW}[1/8]${NC} Checking interface $INTERFACE..."
if ! ip link show "$INTERFACE" &>/dev/null; then
    log_error "Interface $INTERFACE not found!"
    echo -e "\n${YELLOW}Available interfaces:${NC}"
    ip link show | grep -E "^[0-9]+:" | awk '{print "  - " $2}' | sed 's/://'
    echo -e "\n${YELLOW}Hint:${NC} Run ./find_interface.sh to detect WiFi interfaces"
    echo -e "      Then edit config.sh and set INTERFACE to your WiFi adapter"
    exit 1
fi
log_success "Interface $INTERFACE exists"
log_debug "Interface state: $(ip link show $INTERFACE | grep -o 'state [A-Z]*' | awk '{print $2}')"

# Step 2: Stop NetworkManager management of wireless interface
echo -e "\n${YELLOW}[2/8]${NC} Stopping NetworkManager on $INTERFACE..."
log_debug "Running: nmcli device set $INTERFACE managed no"
if nmcli device set $INTERFACE managed no 2>&1 | tee /tmp/nm_stop.log; then
    log_success "NetworkManager stopped managing $INTERFACE"
else
    log_warning "Failed to stop NetworkManager (may not be a problem)"
    log_debug "Output: $(cat /tmp/nm_stop.log)"
fi
sleep 1

# Step 3: Bring down the interface
echo -e "\n${YELLOW}[3/8]${NC} Bringing down interface $INTERFACE..."
log_debug "Running: ip link set $INTERFACE down"
if ip link set $INTERFACE down 2>&1 | tee /tmp/ifdown.log; then
    log_success "Interface brought down"
else
    log_error "Failed to bring down interface"
    cat /tmp/ifdown.log
    exit 1
fi
sleep 1

# Step 4: Configure static IP
echo -e "\n${YELLOW}[4/8]${NC} Configuring static IP $STATIC_IP..."
log_debug "Flushing existing addresses on $INTERFACE"
ip addr flush dev $INTERFACE

log_debug "Adding IP: $STATIC_IP/24 to $INTERFACE"
if ip addr add $STATIC_IP/24 dev $INTERFACE 2>&1 | tee /tmp/ipaddr.log; then
    log_success "IP address configured"
else
    log_error "Failed to configure IP address"
    cat /tmp/ipaddr.log
    exit 1
fi

log_debug "Bringing interface up"
if ip link set $INTERFACE up 2>&1 | tee /tmp/ifup.log; then
    log_success "Interface is up"
    log_debug "Interface state: $(ip link show $INTERFACE | grep -o 'state [A-Z]*' | awk '{print $2}')"
else
    log_error "Failed to bring up interface"
    cat /tmp/ifup.log
    exit 1
fi
sleep 1

# Step 5: Start hostapd
echo -e "\n${YELLOW}[5/8]${NC} Starting hostapd..."
log_debug "Using config: $PROJECT_ROOT/hostapd.conf"
log_debug "Killing any existing hostapd processes"
killall hostapd 2>/dev/null || true

log_debug "Running: hostapd -B $PROJECT_ROOT/hostapd.conf"
if hostapd -B "$PROJECT_ROOT/hostapd.conf" > /tmp/hostapd.log 2>&1; then
    sleep 2
    if pgrep -x "hostapd" > /dev/null; then
        log_success "hostapd started (PID: $(pgrep -x hostapd))"
    else
        log_error "hostapd process not found after start"
        echo -e "\n${YELLOW}hostapd.log contents:${NC}"
        cat /tmp/hostapd.log
        nmcli device set $INTERFACE managed yes
        exit 1
    fi
else
    log_error "hostapd failed to start"
    echo -e "\n${YELLOW}hostapd.log contents:${NC}"
    cat /tmp/hostapd.log
    echo -e "\n${YELLOW}Common issues:${NC}"
    echo "  - Interface may not support AP mode"
    echo "  - Driver issues with your WiFi adapter"
    echo "  - Channel conflict (try changing CHANNEL in config.sh)"
    nmcli device set $INTERFACE managed yes
    exit 1
fi

# Step 6: Start dnsmasq
echo -e "\n${YELLOW}[6/8]${NC} Starting dnsmasq..."
log_debug "Using config: $PROJECT_ROOT/dnsmasq.conf"
log_debug "Killing any existing dnsmasq processes"
killall dnsmasq 2>/dev/null || true

log_debug "Running: dnsmasq -C $PROJECT_ROOT/dnsmasq.conf"
rm -f /tmp/dnsmasq.log # Remove old log to prevent permission errors
touch /tmp/dnsmasq.log && chmod 666 /tmp/dnsmasq.log # Ensure writable
if dnsmasq -C "$PROJECT_ROOT/dnsmasq.conf" --log-facility=/tmp/dnsmasq.log 2>&1 | tee /tmp/dnsmasq_start.log; then
    sleep 1
    if pgrep -x "dnsmasq" > /dev/null; then
        log_success "dnsmasq started (PID: $(pgrep -x dnsmasq))"
    else
        log_error "dnsmasq process not found after start"
        echo -e "\n${YELLOW}dnsmasq startup log:${NC}"
        cat /tmp/dnsmasq_start.log
        killall hostapd 2>/dev/null
        nmcli device set $INTERFACE managed yes
        exit 1
    fi
else
    log_error "dnsmasq failed to start"
    echo -e "\n${YELLOW}dnsmasq error output:${NC}"
    cat /tmp/dnsmasq_start.log
    echo -e "\n${YELLOW}Common issues:${NC}"
    echo "  - Port 53 (DNS) may be in use by another service"
    echo "  - Check with: sudo lsof -i :53"
    killall hostapd 2>/dev/null
    nmcli device set $INTERFACE managed yes
    exit 1
fi

# Step 7: Configure iptables for captive portal
echo -e "\n${YELLOW}[7/8]${NC} Configuring iptables..."
log_debug "Removing old captive portal rules (if any)"
# Instead of flushing ALL rules (iptables -F), we only remove our specific rules
# This prevents breaking other services (Docker, local PHP server firewall, etc.)
iptables -t nat -D PREROUTING -i $INTERFACE -p tcp --dport 80 -j DNAT --to-destination $STATIC_IP:$SERVER_PORT 2>/dev/null || true
iptables -t nat -D PREROUTING -i $INTERFACE -p tcp --dport 443 -j DNAT --to-destination $STATIC_IP:$SERVER_PORT 2>/dev/null || true
iptables -D INPUT -i $INTERFACE -j ACCEPT 2>/dev/null || true
iptables -D OUTPUT -o $INTERFACE -j ACCEPT 2>/dev/null || true

log_debug "Adding NAT rules for HTTP/HTTPS redirect"
iptables -t nat -A PREROUTING -i $INTERFACE -p tcp --dport 80 -j DNAT --to-destination $STATIC_IP:$SERVER_PORT
iptables -t nat -A PREROUTING -i $INTERFACE -p tcp --dport 443 -j DNAT --to-destination $STATIC_IP:$SERVER_PORT

log_debug "Adding INPUT/OUTPUT rules"
iptables -A INPUT -i $INTERFACE -j ACCEPT
iptables -A OUTPUT -o $INTERFACE -j ACCEPT

log_success "iptables configured"
if [ "$VERBOSE" -eq 1 ]; then
    echo -e "${BLUE}NAT rules:${NC}"
    iptables -t nat -L PREROUTING -n | grep -v "^Chain" | grep -v "^target"
fi

# Step 8: Start Python web server
echo -e "\n${YELLOW}[8/8]${NC} Starting web server..."
cd "$PROJECT_ROOT"

log_debug "Checking for Flask installation"
if ! python3 -c "import flask" 2>/dev/null; then
    log_error "Flask is not installed!"
    echo -e "\n${YELLOW}Install Flask with:${NC}"
    echo "  sudo ./install_deps.sh"
    killall dnsmasq 2>/dev/null
    killall hostapd 2>/dev/null
    iptables -t nat -F
    nmcli device set $INTERFACE managed yes
    exit 1
fi
log_debug "Flask is installed"

log_debug "Running: python3 server.py --port $SERVER_PORT"
python3 server.py --port $SERVER_PORT > /tmp/portal-server.log 2>&1 &
SERVER_PID=$!
echo $SERVER_PID > /tmp/portal-server.pid
log_debug "Server started with PID: $SERVER_PID"

sleep 2

# Check if server is running
if kill -0 $SERVER_PID 2>/dev/null; then
    log_success "Web server is running (PID: $SERVER_PID)"
    log_debug "Checking if server is listening on port $SERVER_PORT"
    if ss -tuln | grep -q ":$SERVER_PORT "; then
        log_success "Server is listening on port $SERVER_PORT"
    else
        log_warning "Server may not be listening on port $SERVER_PORT yet (still starting up)"
    fi
else
    log_error "Web server failed to start"
    echo -e "\n${YELLOW}Server log contents:${NC}"
    cat /tmp/portal-server.log
    echo -e "\n${YELLOW}Common issues:${NC}"
    echo "  - Flask not installed: sudo ./install_deps.sh"
    echo "  - Database connection error: check MySQL credentials in config.sh"
    echo "  - Port $SERVER_PORT already in use: sudo lsof -i :$SERVER_PORT"
    killall dnsmasq 2>/dev/null
    killall hostapd 2>/dev/null
    iptables -t nat -F
    nmcli device set $INTERFACE managed yes
    exit 1
fi

echo -e "\n${GREEN}✓ Captive Portal Hotspot is running!${NC}\n"
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${CYAN}Network Information:${NC}"
echo -e "  SSID:        ${GREEN}$SSID${NC}"
echo -e "  Password:    ${GREEN}$WPA_PASSPHRASE${NC}"
echo -e "  Gateway IP:  ${GREEN}$STATIC_IP${NC}"
echo -e "  Interface:   ${GREEN}$INTERFACE${NC}"
echo -e ""
echo -e "${CYAN}Process Information:${NC}"
echo -e "  hostapd:     PID $(pgrep -x hostapd)"
echo -e "  dnsmasq:     PID $(pgrep -x dnsmasq)"
echo -e "  web server:  PID $SERVER_PID"
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e ""
echo -e "${GREEN}✓${NC} Clients will be redirected to the captive portal page automatically."
echo -e "${GREEN}✓${NC} Connect to WiFi and the gaming kiosk will appear!"
echo -e ""
echo -e "To stop the hotspot:  ${YELLOW}sudo ../stop.sh${NC}"
echo -e ""
echo -e "${CYAN}Log Files:${NC}"
echo -e "  hostapd:     /tmp/hostapd.log"
echo -e "  dnsmasq:     /tmp/dnsmasq.log"
echo -e "  web server:  /tmp/portal-server.log"
echo -e ""
echo -e "View logs live: ${YELLOW}tail -f /tmp/portal-server.log${NC}"
echo ""
