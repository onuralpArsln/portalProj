#!/usr/bin/env python3
"""
Test script for server_display notifications.
Tests various message lengths to verify font auto-sizing works correctly.
"""

import time
import server_display

def main():
    print("Initializing display...")

    if not server_display.init_display():
        print("Failed to initialize display. Is DISPLAY set?")
        return

    print("Display initialized. Starting notification tests...\n")
    time.sleep(1)

    # Test cases
    tests = [
        ("center", "Short"),
        ("center", "100 TL YÜKLENDİ"),
        ("top", "Top Short"),
        ("center", "This is a medium length message for testing"),
        ("top", "Medium top notification message here"),
        ("center", "Bu uzun bir test mesajıdır ve birden fazla satıra sarmalıdır, font boyutu otomatik küçülmeli"),
        ("top", "This is a very long message that should automatically shrink the font size to fit within the notification box"),
        ("center", "A " * 50),  # Repeated text
        ("top", "Test " * 30),  # Repeated text for top
    ]

    for i, (position, message) in enumerate(tests, 1):
        print(f"Test {i}/{len(tests)}: [{position}] {message[:40]}{'...' if len(message) > 40 else ''}")

        if position == "center":
            server_display.show_notification(message)
        else:
            server_display.show_notification_top(message)

        time.sleep(2.5)

    print("\nAll tests complete!")

if __name__ == "__main__":
    main()
