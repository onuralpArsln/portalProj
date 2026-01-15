#!/usr/bin/env python3
"""
Server Display Module
Provides Tkinter-based on-screen notifications for server.py
Adapted from kumanda.py notification system
"""

import tkinter as tk
from tkinter import font as tkfont
import threading
import queue
import sys
import os
from math import ceil

# Global variables
root = None
notification_window = None
notification_queue = queue.Queue()
display_thread = None
display_available = False


def _calculate_fitting_font_size(message, available_width, available_height, min_size=10, max_size=150):
    """
    Calculate the largest font size that fits the message within the available space.
    Uses Font.measure() and Font.metrics() for accurate text measurement.

    Args:
        message: Text to display
        available_width: Maximum width in pixels
        available_height: Maximum height in pixels
        min_size: Minimum font size to return
        max_size: Maximum font size to try

    Returns:
        Font size (as negative pixel value for Tkinter)
    """
    if not message:
        return -max_size

    # Try font sizes from max down to min, find the largest that fits
    for size in range(max_size, min_size - 1, -5):
        try:
            f = tkfont.Font(family="Arial", size=-size, weight="bold")

            # Get line height
            line_height = f.metrics("linespace")

            # Measure full text width
            text_width = f.measure(message)

            # Calculate how many lines needed with wrapping
            if text_width <= available_width:
                lines_needed = 1
            else:
                # Estimate lines by dividing total width by available width
                lines_needed = ceil(text_width / available_width)

            # Calculate total height needed
            total_height = lines_needed * line_height

            # Check if it fits
            if total_height <= available_height:
                return -size  # Negative for pixel size in Tkinter

        except Exception:
            continue

    return -min_size  # Fallback to minimum size


def init_display():
    """
    Initialize Tkinter display in a background thread.
    This allows Flask to run without blocking.
    Returns True if display initialized successfully, False otherwise.
    """
    global display_thread, display_available
    
    # Check if we have a display available
    if not os.environ.get('DISPLAY'):
        print("[DISPLAY] No DISPLAY environment variable found. Running headless.")
        display_available = False
        return False
    
    try:
        display_thread = threading.Thread(target=_tkinter_thread, daemon=True)
        display_thread.start()
        display_available = True
        print("[DISPLAY] Notification display initialized successfully")
        return True
    except Exception as e:
        print(f"[DISPLAY] Failed to initialize display: {e}")
        display_available = False
        return False


def _tkinter_thread():
    """Background thread that runs the Tkinter event loop"""
    global root
    
    try:
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        root.attributes('-alpha', 0.0)  # Make it completely transparent
        
        # Process notification queue
        root.after(100, _process_queue)
        
        # Start Tkinter event loop
        root.mainloop()
    except Exception as e:
        print(f"[DISPLAY] Tkinter thread error: {e}")


def _process_queue():
    """Process pending notifications from the queue"""
    global root
    
    if root is None:
        return
    
    try:
        while not notification_queue.empty():
            message, position = notification_queue.get_nowait()
            if position == 'center':
                _show_notification_center(message)
            elif position == 'top':
                _show_notification_top(message)
    except queue.Empty:
        pass
    except Exception as e:
        print(f"[DISPLAY] Queue processing error: {e}")
    
    # Schedule next queue check
    if root:
        root.after(100, _process_queue)


def show_notification(message):
    """
    Show a centered notification on the server screen.
    Thread-safe - can be called from Flask request handlers.
    
    Args:
        message: Text to display
    """
    if not display_available:
        print(f"[NOTIFICATION] {message}")
        return
    
    try:
        notification_queue.put((message, 'center'))
    except Exception as e:
        print(f"[DISPLAY] Failed to queue notification: {e}")


def show_notification_top(message):
    """
    Show a top-positioned notification on the server screen.
    Thread-safe - can be called from Flask request handlers.
    
    Args:
        message: Text to display
    """
    if not display_available:
        print(f"[NOTIFICATION] {message}")
        return
    
    try:
        notification_queue.put((message, 'top'))
    except Exception as e:
        print(f"[DISPLAY] Failed to queue notification: {e}")


def _show_notification_center(message):
    """
    Internal: Display a centered notification window.
    Adapted from kumanda.py show_notification()
    """
    global root, notification_window
    
    if not root:
        return
    
    # Close previous notification if exists
    if notification_window and notification_window.winfo_exists():
        notification_window.destroy()
    
    # Create new notification window
    notification_window = tk.Toplevel(root)
    notification_window.overrideredirect(True)
    notification_window.attributes("-topmost", True)
    
    # Style settings (matching kumanda.py)
    MAIN_BG_COLOR = "#2C3E50"
    BORDER_COLOR = "#FFD700"
    TEXT_COLOR = "#ECF0F1"
    FRAME_BORDER_THICKNESS = 6
    LABEL_PADX = 50
    LABEL_PADY = 40
    
    # Calculate size and position
    root.update_idletasks()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    notification_width = int(screen_width * 0.80)
    notification_height = int(screen_height * 0.25)
    
    x_pos = (screen_width // 2) - (notification_width // 2)
    y_pos = (screen_height // 2) - (notification_height // 2)
    
    notification_window.geometry(f"{notification_width}x{notification_height}+{x_pos}+{y_pos}")
    
    # Calculate font size dynamically
    total_horizontal_padding = (FRAME_BORDER_THICKNESS * 2) + (LABEL_PADX * 2)
    total_vertical_padding = (FRAME_BORDER_THICKNESS * 2) + (LABEL_PADY * 2)
    
    available_width = notification_width - total_horizontal_padding
    available_height = notification_height - total_vertical_padding

    # Calculate font size that fits the message within available space
    dynamic_font_size = _calculate_fitting_font_size(message, available_width, available_height)

    wrap_length_pixels = max(1, available_width)

    # Create frames
    main_frame = tk.Frame(notification_window, bg=BORDER_COLOR,
                         padx=FRAME_BORDER_THICKNESS, pady=FRAME_BORDER_THICKNESS)
    main_frame.pack(expand=True, fill="both")
    
    content_frame = tk.Frame(main_frame, bg=MAIN_BG_COLOR)
    content_frame.pack(expand=True, fill="both")
    
    # Create label
    label = tk.Label(
        content_frame,
        text=message,
        font=("Arial", dynamic_font_size, "bold"),
        fg=TEXT_COLOR,
        bg=MAIN_BG_COLOR,
        padx=LABEL_PADX,
        pady=LABEL_PADY,
        wraplength=wrap_length_pixels,
        justify='center'
    )
    label.pack(expand=True, fill="both")
    
    # Auto-close after 1.5 seconds
    notification_window.after(1500, notification_window.destroy)


def _show_notification_top(message):
    """
    Internal: Display a top-positioned notification window.
    Adapted from kumanda.py show_notification_top()
    """
    global root, notification_window
    
    if not root:
        return
    
    # Close previous notification if exists
    if notification_window and notification_window.winfo_exists():
        notification_window.destroy()
    
    # Create new notification window
    notification_window = tk.Toplevel(root)
    notification_window.overrideredirect(True)
    notification_window.attributes("-topmost", True)
    
    # Style settings
    MAIN_BG_COLOR = "#2C3E50"
    BORDER_COLOR = "#FFD700"
    TEXT_COLOR = "#ECF0F1"
    FRAME_BORDER_THICKNESS = 6
    LABEL_PADX = 50
    LABEL_PADY = 40
    
    # Calculate size and position
    root.update_idletasks()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    notification_width = int(screen_width * 0.80)
    notification_height = int(screen_height * 0.15)
    
    x_pos = (screen_width // 2) - (notification_width // 2)
    y_pos = 0  # Top of screen
    
    notification_window.geometry(f"{notification_width}x{notification_height}+{x_pos}+{y_pos}")
    
    # Calculate font size dynamically
    total_horizontal_padding = (FRAME_BORDER_THICKNESS * 2) + (LABEL_PADX * 2)
    total_vertical_padding = (FRAME_BORDER_THICKNESS * 2) + (LABEL_PADY * 2)
    
    available_width = notification_width - total_horizontal_padding
    available_height = notification_height - total_vertical_padding

    # Calculate font size that fits the message within available space
    dynamic_font_size = _calculate_fitting_font_size(message, available_width, available_height)

    wrap_length_pixels = max(1, available_width)

    # Create frames
    main_frame = tk.Frame(notification_window, bg=BORDER_COLOR,
                         padx=FRAME_BORDER_THICKNESS, pady=FRAME_BORDER_THICKNESS)
    main_frame.pack(expand=True, fill="both")

    content_frame = tk.Frame(main_frame, bg=MAIN_BG_COLOR)
    content_frame.pack(expand=True, fill="both")

    # Create label
    label = tk.Label(
        content_frame,
        text=message,
        font=("Arial", dynamic_font_size, "bold"),
        fg=TEXT_COLOR,
        bg=MAIN_BG_COLOR,
        padx=LABEL_PADX,
        pady=LABEL_PADY,
        wraplength=wrap_length_pixels,
        justify='center'
    )
    label.pack(expand=True, fill="both")

    # Auto-close after 1.5 seconds
    notification_window.after(1500, notification_window.destroy)


if __name__ == "__main__":
    # Test the display module
    print("Testing display module...")
    
    if init_display():
        import time
        
        time.sleep(1)
        show_notification("Test Notification - Center")
        time.sleep(2)
        show_notification_top("Test Notification - Top")
        time.sleep(2)
        show_notification("100 TL YÜKLENDİ")
        time.sleep(2)
        # Test long message that would overflow with old implementation
        show_notification("Bu uzun bir test mesajıdır ve birden fazla satıra sarmalıdır")
        time.sleep(2)
        show_notification_top("Long message test for top notification to verify auto-sizing")
        time.sleep(2)
        
        print("Test complete. Press Ctrl+C to exit.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nExiting...")
    else:
        print("Display initialization failed. Running in headless mode.")
