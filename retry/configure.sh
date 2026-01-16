#!/bin/bash

# ========================================
# Captive Portal - Auto Configuration
# ========================================
# This script automatically finds the wireless interface
# and updates all configuration files accordingly

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}  Captive Portal Auto-Configuration${NC}"
echo -e "${BLUE}=========================================${NC}\n"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${YELLOW}Note: Running without sudo. Some operations may fail.${NC}\n"
fi

# ============================================
# STEP 1: FIND WIRELESS INTERFACE
# ============================================

echo -e "${YELLOW}[1/4]${NC} Detecting wireless interfaces...\n"

# Try multiple methods to find wireless interfaces
WIRELESS_INTERFACES=()

# Method 1: Using ip link (most reliable)
while IFS= read -r iface; do
    if [ -n "$iface" ]; then
        WIRELESS_INTERFACES+=("$iface")
    fi
done < <(ip link show | grep -E "^[0-9]+: (wl|ww)" | awk -F': ' '{print $2}')

# Method 2: Using iwconfig (if available)
if command -v iwconfig &> /dev/null; then
    while IFS= read -r iface; do
        if [ -n "$iface" ] && [[ ! " ${WIRELESS_INTERFACES[@]} " =~ " ${iface} " ]]; then
            WIRELESS_INTERFACES+=("$iface")
        fi
    done < <(iwconfig 2>&1 | grep -v "no wireless" | grep "IEEE" | awk '{print $1}')
fi

# Display found interfaces
if [ ${#WIRELESS_INTERFACES[@]} -eq 0 ]; then
    echo -e "${RED}  ✗ No wireless interfaces found${NC}\n"
    echo -e "Available network interfaces:"
    ip link show | grep -E "^[0-9]+:" | awk -F': ' '{print "  - " $2}'
    echo ""
    echo -e "${YELLOW}Please manually set INTERFACE in config.sh${NC}"
    exit 1
elif [ ${#WIRELESS_INTERFACES[@]} -eq 1 ]; then
    SELECTED_INTERFACE="${WIRELESS_INTERFACES[0]}"
    echo -e "${GREEN}  ✓ Found wireless interface: $SELECTED_INTERFACE${NC}"
else
    echo -e "${GREEN}  ✓ Found multiple wireless interfaces:${NC}"
    for i in "${!WIRELESS_INTERFACES[@]}"; do
        echo -e "    $((i+1)). ${WIRELESS_INTERFACES[$i]}"
    done
    echo ""
    
    # Auto-select the first one, but allow override
    SELECTED_INTERFACE="${WIRELESS_INTERFACES[0]}"
    echo -e "${YELLOW}  → Auto-selecting: $SELECTED_INTERFACE${NC}"
    echo -e "    (To change, edit INTERFACE in config.sh)"
fi

echo ""

# ============================================
# STEP 2: UPDATE CONFIG.SH
# ============================================

echo -e "${YELLOW}[2/4]${NC} Updating config.sh..."

TARGET_DIR="/home/hp"
CONFIG_FILE="$TARGET_DIR/config.sh"

if [ -f "$CONFIG_FILE" ]; then
    # Backup the original config
    if [ ! -f "$CONFIG_FILE.backup" ]; then
        cp "$CONFIG_FILE" "$CONFIG_FILE.backup"
        echo -e "  ${GREEN}✓${NC} Created backup: config.sh.backup"
    fi
    
    # Update the interface in config.sh
    CURRENT_INTERFACE=$(grep "^INTERFACE=" "$CONFIG_FILE" | cut -d'"' -f2)
    
    if [ "$CURRENT_INTERFACE" != "$SELECTED_INTERFACE" ]; then
        sed -i "s/^INTERFACE=.*/INTERFACE=\"$SELECTED_INTERFACE\"/" "$CONFIG_FILE"
        echo -e "  ${GREEN}✓${NC} Updated INTERFACE: $CURRENT_INTERFACE → $SELECTED_INTERFACE"
    else
        echo -e "  ${GREEN}✓${NC} INTERFACE already set to $SELECTED_INTERFACE"
    fi
else
    echo -e "${RED}  ✗ config.sh not found!${NC}"
    exit 1
fi

# Source the config file to get all settings
source "$CONFIG_FILE"

echo ""

# ============================================
# STEP 3: UPDATE SERVICE CONFIGURATION FILES
# ============================================

echo -e "${YELLOW}[3/4]${NC} Updating service configuration files..."

# Update hostapd.conf
if [ -f "$TARGET_DIR/hostapd.conf" ]; then
    if grep -q "^interface=" "$TARGET_DIR/hostapd.conf"; then
        sed -i "s/^interface=.*/interface=$SELECTED_INTERFACE/" "$TARGET_DIR/hostapd.conf"
        echo -e "  ${GREEN}✓${NC} Updated hostapd.conf"
    fi
    
    # Also update SSID and password if they've changed
    if grep -q "^ssid=" "$TARGET_DIR/hostapd.conf"; then
        sed -i "s/^ssid=.*/ssid=$SSID/" "$TARGET_DIR/hostapd.conf"
    fi
    if grep -q "^wpa_passphrase=" "$TARGET_DIR/hostapd.conf"; then
        sed -i "s/^wpa_passphrase=.*/wpa_passphrase=$WPA_PASSPHRASE/" "$TARGET_DIR/hostapd.conf"
    fi
    if grep -q "^channel=" "$TARGET_DIR/hostapd.conf"; then
        sed -i "s/^channel=.*/channel=$CHANNEL/" "$TARGET_DIR/hostapd.conf"
    fi
else
    echo -e "  ${YELLOW}!${NC} hostapd.conf not found at $TARGET_DIR"
fi

# Update dnsmasq.conf
if [ -f "$TARGET_DIR/dnsmasq.conf" ]; then
    if grep -q "^interface=" "$TARGET_DIR/dnsmasq.conf"; then
        sed -i "s/^interface=.*/interface=$SELECTED_INTERFACE/" "$TARGET_DIR/dnsmasq.conf"
        echo -e "  ${GREEN}✓${NC} Updated dnsmasq.conf"
    fi
    
    # Update DHCP range
    if grep -q "^dhcp-range=" "$TARGET_DIR/dnsmasq.conf"; then
        sed -i "s|^dhcp-range=.*|dhcp-range=$DHCP_RANGE_START,$DHCP_RANGE_END,12h|" "$TARGET_DIR/dnsmasq.conf"
    fi
else
    echo -e "  ${YELLOW}!${NC} dnsmasq.conf not found at $TARGET_DIR"
fi

echo ""

# ============================================
# STEP 4: DISPLAY CONFIGURATION SUMMARY
# ============================================

echo -e "${YELLOW}[4/4]${NC} Configuration Summary\n"

echo -e "${BLUE}Network Configuration:${NC}"
echo -e "  Interface:      ${GREEN}$SELECTED_INTERFACE${NC}"
echo -e "  Static IP:      ${GREEN}$STATIC_IP${NC}"
echo -e "  Netmask:        ${GREEN}$NETMASK${NC}"
echo -e "  DHCP Range:     ${GREEN}$DHCP_RANGE_START - $DHCP_RANGE_END${NC}"
echo ""
echo -e "${BLUE}WiFi Hotspot:${NC}"
echo -e "  SSID:           ${GREEN}$SSID${NC}"
echo -e "  Password:       ${GREEN}$WPA_PASSPHRASE${NC}"
echo -e "  Channel:        ${GREEN}$CHANNEL${NC}"
echo ""
echo -e "${BLUE}Server:${NC}"
echo -e "  Port:           ${GREEN}$SERVER_PORT${NC}"
echo ""

if [ -n "$MYSQL_DATABASE" ]; then
    echo -e "${BLUE}Database:${NC}"
    echo -e "  Database:       ${GREEN}$MYSQL_DATABASE${NC}"
    echo -e "  User:           ${GREEN}$MYSQL_USER${NC}"
    echo -e "  User ID:        ${GREEN}$USER_ID${NC}"
    echo -e "  Shop ID:        ${GREEN}$SHOP_ID${NC}"
    echo ""
fi

echo -e "${BLUE}=========================================${NC}"
echo -e "${GREEN}✓ Configuration Complete!${NC}"
echo -e "${BLUE}=========================================${NC}\n"

echo -e "Configuration saved to: ${YELLOW}$CONFIG_FILE${NC}"
echo -e ""
echo -e "To modify settings manually:"
echo -e "  ${YELLOW}nano $CONFIG_FILE${NC}"
echo -e "  Then run ${YELLOW}sudo ./configure.sh${NC} again"
echo -e ""
echo -e "To start the captive portal:"
echo -e "  ${YELLOW}sudo ./start.sh${NC}"
echo ""
