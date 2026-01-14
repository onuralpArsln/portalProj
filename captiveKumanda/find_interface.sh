#!/bin/bash
# Helper script to find available wireless interfaces
# Run this to see what WiFi interface names are available on your system

echo "========================================="
echo "Available Wireless Network Interfaces"
echo "========================================="
echo ""

# Method 1: Using ip link
echo "Method 1: Using 'ip link show'"
echo "-------------------------------"
ip link show | grep -E "^[0-9]+: (wl|ww)" | awk '{print $2}' | sed 's/://' | while read iface; do
    echo "  ✓ $iface"
done

echo ""

# Method 2: Using iwconfig
if command -v iwconfig &> /dev/null; then
    echo "Method 2: Using 'iwconfig'"
    echo "-------------------------------"
    iwconfig 2>&1 | grep -v "no wireless" | grep "IEEE" | awk '{print $1}' | while read iface; do
        echo "  ✓ $iface"
    done
    echo ""
fi

# Method 3: List all network interfaces (for reference)
echo "All Network Interfaces:"
echo "-------------------------------"
ip link show | grep -E "^[0-9]+:" | awk '{print $2}' | sed 's/://' | while read iface; do
    state=$(ip link show "$iface" | grep -o "state [A-Z]*" | awk '{print $2}')
    echo "  - $iface (state: $state)"
done

echo ""
echo "========================================="
echo "💡 Update config.sh with your interface:"
echo "   INTERFACE=\"your_interface_name\""
echo "========================================="
