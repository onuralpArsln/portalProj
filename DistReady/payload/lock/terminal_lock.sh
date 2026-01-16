#!/bin/bash
# Terminal Password Lock
# This script runs on EVERY new terminal/shell session
# Prompts for password and shuts down device if wrong

CORRECT_PASSWORD="131619"
MAX_ATTEMPTS=3

# Skip password check if already verified in this session
if [ "$TERMINAL_LOCKED" = "verified" ]; then
    return 0 2>/dev/null || exit 0
fi

# Clear screen for security
clear

echo "========================================"
echo "    TERMINAL ACCESS VERIFICATION"
echo "========================================"
echo ""

attempt=1
while [ $attempt -le $MAX_ATTEMPTS ]; do
    echo -n "Enter password (Attempt $attempt/$MAX_ATTEMPTS): "
    read -s password
    echo ""
    
    if [ "$password" = "$CORRECT_PASSWORD" ]; then
        echo ""
        echo "✓ Access granted"
        echo ""
        # Mark this session as verified
        export TERMINAL_LOCKED="verified"
        return 0 2>/dev/null || exit 0
    else
        echo "✗ Incorrect password"
        echo ""
        ((attempt++))
    fi
done

# All attempts failed - shutdown device
echo "========================================"
echo "  ACCESS DENIED - SHUTTING DOWN SYSTEM"
echo "========================================"
echo ""
sleep 2

# Shutdown the device
sudo shutdown -h now 2>/dev/null || shutdown -h now 2>/dev/null

# If shutdown fails (not root), just exit terminal
exit 1
