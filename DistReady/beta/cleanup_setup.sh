#!/bin/bash

# Captive Portal Setup Cleanup
# Reverts immutability and removes generated configuration files and license.

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${BLUE}=======================================${NC}"
echo -e "${BLUE}  Captive Portal Setup Cleanup${NC}"
echo -e "${BLUE}=======================================${NC}\n"

if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Error: Must run as root (sudo)${NC}"
   exit 1
fi

FILES_TO_REMOVE=(
    "$PROJECT_ROOT/config.sh"
    "$PROJECT_ROOT/hostapd.conf"
    "$PROJECT_ROOT/dnsmasq.conf"
    "$PROJECT_ROOT/security/dlI"
)

echo -e "${YELLOW}[1/2] Reverting immutability (chattr -i)...${NC}"

for file in "${FILES_TO_REMOVE[@]}"; do
    if [ -f "$file" ]; then
        if chattr -i "$file"; then
             echo -e "  ${GREEN}✓${NC} Unlocked $file"
        else
             echo -e "  ${RED}✗ Failed to unlock $file${NC}"
        fi
    else
        echo -e "  ${YELLOW}?${NC} File not found: $file (skipping unlock)"
    fi
done

echo -e "\n${YELLOW}[2/2] Deleting files...${NC}"

for file in "${FILES_TO_REMOVE[@]}"; do
    if [ -f "$file" ]; then
        if rm -f "$file"; then
             echo -e "  ${GREEN}✓${NC} Deleted $file"
        else
             echo -e "  ${RED}✗ Failed to delete $file${NC}"
        fi
    else
        echo -e "  ${YELLOW}?${NC} File not found: $file (skipping delete)"
    fi
done

echo -e "\n${BLUE}=======================================${NC}"
echo -e "${GREEN}✓ Cleanup Complete!${NC}"
echo -e "${BLUE}=======================================${NC}"
