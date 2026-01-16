#!/bin/bash

# Create Distribution Package
# Bundles executable + setup/lock/security folders for deployment

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Creating Distribution Package${NC}"
echo -e "${BLUE}========================================${NC}\n"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if executable exists
if [ ! -f "dist/captive_portal" ]; then
    echo -e "${RED}Error: Executable not found${NC}"
    echo -e "Run ${YELLOW}./build_executable.sh${NC} first"
    exit 1
fi

# Create package directory
PKG_DIR="dist/captive_portal_package"
echo -e "${YELLOW}[1/4]${NC} Creating package directory...\n"
rm -rf "$PKG_DIR"
mkdir -p "$PKG_DIR"
echo -e "${GREEN}✓${NC} Directory created: $PKG_DIR\n"

# Copy executable
echo -e "${YELLOW}[2/4]${NC} Copying executable...\n"
cp dist/captive_portal "$PKG_DIR/"
chmod +x "$PKG_DIR/captive_portal"
echo -e "${GREEN}✓${NC} Executable copied\n"

# Copy support folders
echo -e "${YELLOW}[3/4]${NC} Copying support folders...\n"

if [ -d "setup" ]; then
    cp -r setup "$PKG_DIR/"
    echo -e "  ${GREEN}✓${NC} setup/"
else
    echo -e "  ${YELLOW}!${NC} setup/ not found (optional)"
fi

if [ -d "lock" ]; then
    cp -r lock "$PKG_DIR/"
    echo -e "  ${GREEN}✓${NC} lock/"
else
    echo -e "  ${YELLOW}!${NC} lock/ not found (optional)"
fi

if [ -d "security" ]; then
    cp -r security "$PKG_DIR/"
    echo -e "  ${GREEN}✓${NC} security/"
else
    echo -e "  ${YELLOW}!${NC} security/ not found (optional)"
fi

echo ""

# Create README for package
echo -e "${YELLOW}[4/4]${NC} Creating deployment README...\n"
cat > "$PKG_DIR/README_DEPLOYMENT.txt" <<'EOF'
# Captive Portal - Deployment Package

## Contents:
- captive_portal       : Main executable (bundled, self-contained)
- setup/               : Installation scripts for dependencies
- lock/                : Terminal password lock system
- security/            : License generation tools

## Deployment Steps:

### 1. Install Dependencies & Generate Configs
cd captive_portal_package
sudo ./setup/install_offline.sh

This automatically:
- Installs system packages
- Installs Python packages
- Generates config.sh, hostapd.conf, dnsmasq.conf
- Detects WiFi interface
- Generates hardware license (dlI)

### 2. Install Terminal Lock (Optional)
cd lock
sudo ./deploy_terminal_lock.sh
cd ..

### 3. Deploy to Production
sudo mkdir -p /opt/captive_portal
sudo cp captive_portal /opt/captive_portal/
sudo cp config.sh /opt/captive_portal/
sudo cp hostapd.conf /opt/captive_portal/
sudo cp dnsmasq.conf /opt/captive_portal/
sudo cp security/dlI /opt/captive_portal/

### 4. Cleanup (Delete temp folders)
rm -rf setup/ lock/ security/

### 5. Run
cd /opt/captive_portal
sudo ./captive_portal

## Final Structure:
/opt/captive_portal/
├── captive_portal       (executable)
├── config.sh
├── hostapd.conf
├── dnsmasq.conf
└── dlI

## Notes:
- The executable is ~40-50MB and contains all dependencies
- Config files (config.sh, hostapd.conf, dnsmasq.conf, dlI) MUST be in the same directory as the executable
- Run with sudo (requires root privileges)
EOF

echo -e "${GREEN}✓${NC} README created\n"

# Display package info
PKG_SIZE=$(du -sh "$PKG_DIR" | cut -f1)

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✓ Package Created!${NC}"
echo -e "${BLUE}========================================${NC}\n"

echo -e "Package location: ${YELLOW}$PKG_DIR${NC}"
echo -e "Package size:     ${YELLOW}$PKG_SIZE${NC}\n"

echo -e "${CYAN}Contents:${NC}"
ls -lh "$PKG_DIR/" | tail -n +2 | awk '{printf "  %s  %s\n", $9, $5}'
echo ""

echo -e "${CYAN}Next Steps:${NC}"
echo -e "  1. Copy package to target device:"
echo -e "     ${YELLOW}scp -r $PKG_DIR/ user@device:/path/${NC}"
echo -e ""
echo -e "  2. On target device, follow deployment steps in:"
echo -e "     ${YELLOW}README_DEPLOYMENT.txt${NC}"
echo ""
