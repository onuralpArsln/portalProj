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
    
    def send_redirect(self, location):
        """Send HTTP 302 redirect"""
        self.send_response(302)
        self.send_header('Location', location)
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        self.end_headers()
    
    def send_captive_redirect(self, location):
        """Send HTML page that redirects - more reliable for captive portal detection"""
        html = f'''<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="refresh" content="0;url={location}">
    <script>window.location.href="{location}";</script>
</head>
<body>
    <h1>Redirecting...</h1>
    <p><a href="{location}">Click here if not redirected</a></p>
</body>
</html>'''
        content = html.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', len(content))
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.end_headers()
        self.wfile.write(content)
    
    def do_GET(self):
        """Handle GET requests"""
        path = urlparse(self.path).path
        client_ip = self.get_client_ip()
        
        portal_url = f'http://{PORTAL_IP}/portal'
        
        # Android captive portal detection - return non-204 to trigger popup
        if path in ['/generate_204', '/gen_204']:
            print(f"📱 Android device detected: {client_ip}")
            self.send_captive_redirect(portal_url)
        
        # iOS/macOS captive portal detection
        elif path in ['/hotspot-detect.html', '/success.txt', '/library/test/success.html']:
            print(f"📱 iOS/macOS device detected: {client_ip}")
            self.send_captive_redirect(portal_url)
        
        # Windows captive portal detection
        elif path in ['/ncsi.txt', '/connecttest.txt', '/redirect']:
            print(f"📱 Windows device detected: {client_ip}")
            self.send_captive_redirect(portal_url)
        
        # Firefox/Other
        elif path in ['/canonical.html', '/kindle-wifi/wifistub.html', '/check_network_status.txt']:
            print(f"📱 Device detected: {client_ip}")
            self.send_captive_redirect(portal_url)
        
        elif path == '/portal' or path == '/':
            self.send_portal_page()
        
        else:
            # Any other path - redirect to portal
            self.send_captive_redirect(portal_url)
    
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
