#!/bin/bash

# Captive Portal Hotspot - Unified Installation Script
# This script installs all dependencies and configures the captive portal system
# Run with: sudo ./install.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}  Captive Portal - Full Setup${NC}"
echo -e "${BLUE}=====================================${NC}\n"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Error: This script must be run as root (use sudo)${NC}"
   exit 1
fi

# ============================================
# PART 1: SYSTEM DEPENDENCIES
# ============================================

# Step 1: Detect wireless interface
echo -e "${YELLOW}[1/9]${NC} Detecting wireless interface..."
WIRELESS_IFACE=$(ip link show | grep -E "^[0-9]+: w" | awk -F': ' '{print $2}' | head -n1)

if [ -z "$WIRELESS_IFACE" ]; then
    echo -e "${RED}  ✗ No wireless interface found${NC}"
    echo "  Available interfaces:"
    ip link show | grep "^[0-9]" | awk -F': ' '{print "    - " $2}'
    exit 1
else
    echo -e "${GREEN}  ✓ Found wireless interface: $WIRELESS_IFACE${NC}"
fi

# Step 2: Check for required system packages
echo -e "\n${YELLOW}[2/9]${NC} Checking required system packages..."

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

# Check pip3
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}  ✗ pip3 not found${NC}"
    MISSING_PACKAGES="$MISSING_PACKAGES python3-pip"
else
    echo -e "${GREEN}  ✓ pip3 installed${NC}"
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

# Step 3: Install missing system packages
if [ -n "$MISSING_PACKAGES" ]; then
    echo -e "\n${YELLOW}[3/9]${NC} Installing missing system packages..."
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
    echo -e "${GREEN}  ✓ System packages installed${NC}"
else
    echo -e "\n${YELLOW}[3/9]${NC} ${GREEN}All required system packages are installed${NC}"
fi

# ============================================
# PART 2: PYTHON DEPENDENCIES
# ============================================

# Step 4: Install Python system packages
echo -e "\n${YELLOW}[4/9]${NC} Installing Python system packages..."

# Detect package manager and install Python packages
if command -v apt-get &> /dev/null; then
    apt-get install -y python3-flask python3-psutil python3-tk 2>/dev/null || {
        echo -e "${YELLOW}  ! Some Python system packages not available via apt${NC}"
    }
    echo -e "${GREEN}  ✓ Python system packages installation attempted${NC}"
elif command -v yum &> /dev/null; then
    yum install -y python3-flask python3-psutil python3-tkinter 2>/dev/null || {
        echo -e "${YELLOW}  ! Some Python system packages not available via yum${NC}"
    }
    echo -e "${GREEN}  ✓ Python system packages installation attempted${NC}"
else
    echo -e "${YELLOW}  ! Skipping system Python packages (will install via pip)${NC}"
fi

# Step 5: Install MySQL connector via pip
echo -e "\n${YELLOW}[5/9]${NC} Installing MySQL connector..."
pip3 install mysql-connector-python==8.2.0 --break-system-packages 2>/dev/null || \
pip3 install mysql-connector-python==8.2.0 || {
    echo -e "${YELLOW}  ! MySQL connector installation may have failed${NC}"
}
echo -e "${GREEN}  ✓ MySQL connector installed${NC}"

# Step 6: Install Flask and psutil via pip (if system packages failed)
echo -e "\n${YELLOW}[6/9]${NC} Ensuring Flask and psutil are available..."
pip3 install flask psutil --break-system-packages 2>/dev/null || \
pip3 install flask psutil || {
    echo -e "${YELLOW}  ! Flask/psutil may already be installed${NC}"
}
echo -e "${GREEN}  ✓ Flask and psutil verified${NC}"

# Step 7: Verify Tkinter installation
echo -e "\n${YELLOW}[7/9]${NC} Verifying Tkinter installation..."
if python3 -c "import tkinter" 2>/dev/null; then
    echo -e "${GREEN}  ✓ Tkinter is installed and working${NC}"
else
    echo -e "${YELLOW}  ⚠ Warning: Tkinter installation may have failed${NC}"
    echo "    Server will run in headless mode without on-screen notifications"
fi

# ============================================
# PART 3: CONFIGURATION
# ============================================

# Step 8: Update configuration files with detected interface
echo -e "\n${YELLOW}[8/9]${NC} Updating config.sh with detected interface..."

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Update config.sh with the detected wireless interface
if [ -f "$PROJECT_ROOT/config.sh" ]; then
    # Backup config.sh if not already backed up
    if [ ! -f "$PROJECT_ROOT/config.sh.backup" ]; then
        cp "$PROJECT_ROOT/config.sh" "$PROJECT_ROOT/config.sh.backup"
        echo -e "  ${GREEN}✓${NC} Created backup: config.sh.backup"
    fi
    
    # Update the interface in config.sh
    CURRENT_IFACE=$(grep "^INTERFACE=" "$PROJECT_ROOT/config.sh" | cut -d'"' -f2)
    
    if [ "$CURRENT_IFACE" != "$WIRELESS_IFACE" ]; then
        sed -i "s/^INTERFACE=.*/INTERFACE=\"$WIRELESS_IFACE\"/" "$PROJECT_ROOT/config.sh"
        echo -e "  ${GREEN}✓${NC} Updated config.sh: INTERFACE=$CURRENT_IFACE → $WIRELESS_IFACE"
    else
        echo -e "  ${GREEN}✓${NC} config.sh already has INTERFACE=$WIRELESS_IFACE"
    fi
    
    echo -e "  ${GREEN}✓${NC} All scripts will now use config.sh for configuration"
else
    echo -e "${YELLOW}  ! config.sh not found${NC}"
    echo -e "  Note: Scripts expect config.sh in the project root"
fi


# ============================================
# PART 4: VERIFICATION
# ============================================

# Step 9: Verify required files and set permissions
echo -e "\n${YELLOW}[9/9]${NC} Verifying project files and setting permissions..."

REQUIRED_FILES=("config.sh" "hostapd.conf" "dnsmasq.conf" "start.sh" "stop.sh" "server.py" "portal.html" "config_loader.py")
MISSING_FILES=""
FOUND_FILES=0

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$PROJECT_ROOT/$file" ]; then
        echo -e "  ${GREEN}✓${NC} $file"
        FOUND_FILES=$((FOUND_FILES + 1))
        
        # Make scripts executable
        if [[ "$file" == *.sh ]] || [[ "$file" == *.py ]]; then
            chmod +x "$PROJECT_ROOT/$file"
        fi
    else
        echo -e "  ${YELLOW}!${NC} $file (missing)"
        MISSING_FILES="$MISSING_FILES $file"
    fi
done

# Make install.sh and configure.sh executable
chmod +x "$PROJECT_ROOT/install.sh" 2>/dev/null || true
chmod +x "$PROJECT_ROOT/configure.sh" 2>/dev/null || true


# Summary
echo -e "\n${BLUE}=====================================${NC}"
echo -e "${GREEN}✓ Installation Complete!${NC}"
echo -e "${BLUE}=====================================${NC}\n"

echo -e "System Dependencies:"
echo -e "  ${GREEN}✓${NC} hostapd, dnsmasq, iptables"
echo -e "  ${GREEN}✓${NC} Python 3 and pip"
echo -e ""
echo -e "Python Dependencies:"
echo -e "  ${GREEN}✓${NC} Flask (web server)"
echo -e "  ${GREEN}✓${NC} psutil (system monitoring)"
echo -e "  ${GREEN}✓${NC} MySQL connector"
if python3 -c "import tkinter" 2>/dev/null; then
    echo -e "  ${GREEN}✓${NC} Tkinter (GUI notifications)"
else
    echo -e "  ${YELLOW}⚠${NC} Tkinter (headless mode)"
fi
echo -e ""
echo -e "Configuration:"
echo -e "  Wireless Interface: ${GREEN}$WIRELESS_IFACE${NC}"
echo -e "  SSID: ${GREEN}CaptivePortal${NC}"
echo -e "  Password: ${GREEN}portal123${NC}"
echo -e "  Gateway IP: ${GREEN}192.168.4.1${NC}"
echo -e ""

if [ $FOUND_FILES -gt 0 ]; then
    echo -e "To configure the system (auto-detect interface):"
    echo -e "  ${YELLOW}sudo ./configure.sh${NC}"
    echo -e ""
    echo -e "To start the captive portal:"
    echo -e "  ${YELLOW}sudo ./start.sh${NC}"
    echo -e ""
    echo -e "To stop the captive portal:"
    echo -e "  ${YELLOW}sudo ./stop.sh${NC}"
else
    echo -e "${YELLOW}Note:${NC} Some required files are missing."
    echo -e "  Dependencies are installed. Please ensure all project files exist."
fi
echo -e ""

# Optional: Check if hostapd/dnsmasq services are enabled
if systemctl is-enabled hostapd &> /dev/null || systemctl is-enabled dnsmasq &> /dev/null; then
    echo -e "${YELLOW}Warning:${NC} hostapd or dnsmasq system services are enabled."
    echo -e "  This may conflict with the manual startup. Consider disabling:"
    echo -e "  ${YELLOW}sudo systemctl disable hostapd dnsmasq${NC}"
    echo -e "  ${YELLOW}sudo systemctl stop hostapd dnsmasq${NC}"
    echo -e ""
fi
