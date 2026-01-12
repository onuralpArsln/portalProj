#!/usr/bin/env python3
"""
Captive Portal Web Server
Serves the portal page and logs button clicks to terminal
"""

import http.server
import socketserver
import json
from datetime import datetime
from urllib.parse import urlparse
import os

PORT = 80
PORTAL_IP = "192.168.4.1"

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

class CaptivePortalHandler(http.server.BaseHTTPRequestHandler):
    
    def log_message(self, format, *args):
        """Override to customize logging"""
        pass  # Suppress default logging
    
    def get_client_ip(self):
        """Get the client's IP address"""
        return self.client_address[0]
    
    def send_portal_page(self):
        """Send the main portal HTML page"""
        try:
            with open(os.path.join(SCRIPT_DIR, 'portal.html'), 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404, "Portal page not found")
    
    def send_json(self, data, status=200):
        """Send JSON response"""
        content = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(content))
        self.end_headers()
        self.wfile.write(content)
    
    def do_GET(self):
        """Handle GET requests"""
        path = urlparse(self.path).path
        client_ip = self.get_client_ip()
        
        # Captive portal detection URLs - redirect to portal
        captive_portal_paths = [
            '/generate_204',           # Android
            '/gen_204',                 # Android
            '/hotspot-detect.html',    # iOS/macOS
            '/success.txt',            # iOS
            '/library/test/success.html',  # macOS
            '/ncsi.txt',               # Windows
            '/connecttest.txt',        # Windows
            '/redirect',               # Windows
            '/canonical.html',         # Firefox
        ]
        
        if path in captive_portal_paths or path == '/':
            self.send_portal_page()
        elif path == '/portal':
            self.send_portal_page()
        elif path.endswith('.html'):
            self.send_portal_page()
        else:
            # For any other path, serve the portal
            self.send_portal_page()
    
    def do_POST(self):
        """Handle POST requests"""
        path = urlparse(self.path).path
        client_ip = self.get_client_ip()
        
        if path == '/click':
            # Read the request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            
            try:
                data = json.loads(body.decode('utf-8'))
                button = data.get('button', 'unknown')
                
                # Log to terminal with timestamp and client IP
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(f"\n{'='*50}")
                print(f"🔘 BUTTON CLICK DETECTED!")
                print(f"{'='*50}")
                print(f"⏰ Time:      {timestamp}")
                print(f"📍 Client IP: {client_ip}")
                print(f"🎯 Button:    Button {button}")
                print(f"{'='*50}\n")
                
                self.send_json({'status': 'ok', 'button': button})
                
            except json.JSONDecodeError:
                self.send_json({'error': 'Invalid JSON'}, 400)
        else:
            self.send_json({'error': 'Not found'}, 404)


def main():
    # Allow socket reuse
    socketserver.TCPServer.allow_reuse_address = True
    
    print(f"""
╔══════════════════════════════════════════════════════════╗
║           🌐 CAPTIVE PORTAL SERVER STARTED 🌐            ║
╠══════════════════════════════════════════════════════════╣
║  Server running on: http://{PORTAL_IP}:{PORT}                  ║
║  Waiting for button clicks from connected devices...     ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    with socketserver.TCPServer(("", PORT), CaptivePortalHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n🛑 Server shutting down...")
            httpd.shutdown()


if __name__ == "__main__":
    main()
