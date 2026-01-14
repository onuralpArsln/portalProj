#!/bin/bash
# ========================================
# Captive Portal Configuration
# ========================================
# Edit this file to configure your captive portal settings
# All scripts will read from this configuration

# WiFi Interface Name
# Common values:
#   - wlan0 (most common)
#   - wlan1 (if you have multiple WiFi adapters)
#   - wlp3s0 (some modern systems)
#   - wlp2s0b1 (USB WiFi adapters)
# To find your interface: ip link show
INTERFACE="wlan0"

# Network Configuration
STATIC_IP="192.168.4.1"
NETMASK="255.255.255.0"
DHCP_RANGE_START="192.168.4.2"
DHCP_RANGE_END="192.168.4.20"

# WiFi Hotspot Settings (used in hostapd.conf)
SSID="CaptivePortal"
WPA_PASSPHRASE="portal123"
CHANNEL="7"

# Server Configuration
SERVER_PORT="80"  # Port 80 for captive portal (requires sudo)

# Database Configuration (for gaming kiosk)
MYSQL_USER="fungames"
MYSQL_PASSWORD="7396Ksn!"
MYSQL_DATABASE="fungames"
USER_ID="320"
SHOP_ID="1"
