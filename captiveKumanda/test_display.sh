#!/bin/bash
# Test script for server-side notifications
# Run this to verify the display module works

echo "================================================"
echo "Server Display Notification Test"
echo "================================================"
echo ""

# Check if DISPLAY is available
if [ -z "$DISPLAY" ]; then
    echo "⚠️  WARNING: No DISPLAY environment variable found"
    echo "   Notifications will print to console only"
    echo ""
else
    echo "✓ Display available: $DISPLAY"
    echo ""
fi

# Test importing the module
echo "Testing module import..."
python3 -c "import server_display; print('✓ server_display module imported successfully')" || {
    echo "❌ Failed to import server_display module"
    exit 1
}

echo ""
echo "Testing server.py with display integration..."
python3 -c "import server; print('✓ server.py loaded successfully')" || {
    echo "❌ Failed to load server.py"
    exit 1
}

echo ""
echo "================================================"
echo "✓ All import tests passed!"
echo "================================================"
echo ""
echo "To test notifications visually:"
echo "  1. Start server: python3 server.py"
echo "  2. Connect from client browser"
echo "  3. Click any button (e.g., '100 ₺')"
echo "  4. Watch server screen for notification"
echo ""
