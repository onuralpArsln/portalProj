#!/bin/bash

# Captive Portal - Build Executable Script
# Creates a single bundled executable using PyInstaller

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Captive Portal - Build Executable${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

echo -e "${YELLOW}[1/5]${NC} Installing build dependencies...\n"
pip3 install --upgrade pip
pip3 install -r requirements.txt
echo -e "${GREEN}✓${NC} Dependencies installed\n"

# Check if required files exist
echo -e "${YELLOW}[2/5]${NC} Checking required files...\n"
REQUIRED_FILES=(
    "captive_portal_main.py"
    "captive_portal.spec"
    "server.py"
    "server_display.py"
    "config_loader.py"
    "portal.html"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}✗ Missing required file: $file${NC}"
        exit 1
    fi
    echo -e "  ${GREEN}✓${NC} $file"
done
echo ""

# Clean previous builds
echo -e "${YELLOW}[3/5]${NC} Cleaning previous builds...\n"
rm -rf build/ dist/
echo -e "${GREEN}✓${NC} Clean complete\n"

# Build executable
echo -e "${YELLOW}[4/5]${NC} Building executable with PyInstaller...\n"
echo -e "${BLUE}This may take a few minutes...${NC}\n"
pyinstaller --clean captive_portal.spec

if [ ! -f "dist/captive_portal" ]; then
    echo -e "\n${RED}✗ Build failed - executable not found${NC}"
    exit 1
fi

echo -e "\n${GREEN}✓${NC} Executable built successfully\n"

# Display executable info
echo -e "${YELLOW}[5/5]${NC} Build information...\n"
EXEC_SIZE=$(du -h dist/captive_portal | cut -f1)
echo -e "  Executable: ${GREEN}dist/captive_portal${NC}"
echo -e "  Size:       ${YELLOW}$EXEC_SIZE${NC}"
echo -e "  Location:   ${BLUE}$SCRIPT_DIR/dist/${NC}"
echo ""

# Make executable
chmod +x dist/captive_portal

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✓ Build Complete!${NC}"
echo -e "${BLUE}========================================${NC}\n"

echo -e "Executable location: ${YELLOW}dist/captive_portal${NC}\n"

echo -e "${CYAN}Next Steps:${NC}"
echo -e "  1. Test the executable:"
echo -e "     ${YELLOW}cd dist${NC}"
echo -e "     ${YELLOW}sudo ./captive_portal${NC}"
echo -e ""
echo -e "  2. Or create distribution package:"
echo -e "     ${YELLOW}./create_package.sh${NC}"
echo ""
