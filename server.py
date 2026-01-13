#!/usr/bin/env python3
"""
Captive Portal Web Server
Simple HTTP server that serves the captive portal landing page
"""

import http.server
import socketserver
import os
import signal
import sys
from datetime import datetime

# Configuration
PORT = 80
PORTAL_PAGE = "portal.html"


class CaptivePortalHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP handler for captive portal"""
    
    def do_GET(self):
        """Handle GET requests - serve portal page for all requests"""
        # Log the request
        client_ip = self.client_address[0]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Request from {client_ip}: {self.path}")
        
        # Serve the portal page regardless of what's requested
        # This is essential for captive portal detection
        try:
            with open(PORTAL_PAGE, 'rb') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', len(content))
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.end_headers()
            self.wfile.write(content)
            
        except FileNotFoundError:
            self.send_error(404, f"Portal page not found: {PORTAL_PAGE}")
        except Exception as e:
            self.send_error(500, f"Server error: {str(e)}")
    
    def do_POST(self):
        """Handle POST requests - redirect to GET"""
        self.do_GET()
    
    def log_message(self, format, *args):
        """Override to customize logging"""
        # Suppress default logging since we have our own
        pass


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully"""
    print("\n\nShutting down captive portal server...")
    sys.exit(0)


def main():
    """Main server function"""
    # Register signal handlers for clean shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Check if portal page exists
    if not os.path.exists(PORTAL_PAGE):
        print(f"Error: {PORTAL_PAGE} not found in current directory")
        sys.exit(1)
    
    # Create and configure server
    socketserver.TCPServer.allow_reuse_address = True
    
    try:
        with socketserver.TCPServer(("", PORT), CaptivePortalHandler) as httpd:
            print(f"Captive Portal Server started on port {PORT}")
            print(f"Serving: {PORTAL_PAGE}")
            print(f"Press Ctrl+C to stop (or use stop.sh)\n")
            
            # Serve forever
            httpd.serve_forever()
            
    except PermissionError:
        print(f"Error: Permission denied to bind to port {PORT}")
        print("Please run with sudo: sudo python3 server.py")
        sys.exit(1)
    except OSError as e:
        print(f"Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
