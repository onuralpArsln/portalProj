#!/usr/bin/env python3
"""
master.py - Ana Kontrol Sistemi

Bu script, tüm bileşenleri tek bir komutla başlatır:
1. Mock Arduino (socat sanal seri port)
2. kumanda.py (wrapper ile, değiştirilmeden)
3. Captive Portal sunucusu (WiFi hotspot ile birlikte)

Portal butonları Arduino komutlarına eşlenir.

KULLANIM:
    sudo python3 master.py

NOT: 
- Hotspot için root (sudo) gerekli
- Önce start_hotspot.sh yerine bu script'i kullanın
"""

import os
import sys
import subprocess
import threading
import time
import signal
import pty
import select
from collections import namedtuple
from queue import Queue
import json
from datetime import datetime

# HTTP server imports
import http.server
import socketserver
from urllib.parse import urlparse

# Serial imports
import serial

# =====================================================
# CONFIGURATION
# =====================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Network settings
INTERFACE = "wlp5s0"
IP_ADDR = "192.168.4.1"
PORT = 80

# Virtual serial ports
VIRTUAL_PORT_ARDUINO = "/tmp/ttyVirtual0"  # Mock Arduino side
VIRTUAL_PORT_KUMANDA = "/tmp/ttyVirtual1"  # kumanda.py side

# Arduino settings
FAKE_VID = 0x1A86  # CH340 VID
FAKE_PID = 0x7523  # CH340 PID
BAUD_RATE = 9600

# Command mapping (portal button -> Arduino code)
COMMANDS = {
    'auth': None,  # Populated at runtime with computer ID
    'sil': '3217',
    'yukle5': '3117',
    'yukle10': '3127',
    'yukle20': '3147',
    'yukle50': '31107',
    'yukle100': '3567',
    'yukle1': '3131',
    'yukle500': '3687',
    'oyun': '3357',
    'kazanc': '4455',
}

# =====================================================
# GLOBAL STATE
# =====================================================

command_queue = Queue()  # Commands from portal to Arduino
mock_serial = None       # Mock Arduino serial connection
socat_process = None     # socat process
running = True           # Global running flag


# =====================================================
# UTILITY FUNCTIONS
# =====================================================

def log(component, message, level="INFO"):
    """Unified logging with timestamp and component tag."""
    timestamp = datetime.now().strftime('%H:%M:%S')
    colors = {
        "INFO": "\033[0m",      # Default
        "OK": "\033[92m",       # Green
        "WARN": "\033[93m",     # Yellow
        "ERROR": "\033[91m",    # Red
        "CMD": "\033[96m",      # Cyan
    }
    color = colors.get(level, colors["INFO"])
    reset = "\033[0m"
    print(f"{color}[{timestamp}] [{component}] {message}{reset}")


def get_computer_id():
    """Calculate computer ID (same as kumanda.py)."""
    import hashlib
    try:
        result = subprocess.check_output("cat /etc/machine-id", shell=True).decode()
        uuid = result.strip()
    except:
        uuid = "unknown"
    return hashlib.sha256(uuid.encode()).hexdigest()[:14]


# =====================================================
# MOCK ARDUINO COMPONENT
# =====================================================

class MockArduino:
    """Simulates Arduino communication over virtual serial port."""
    
    def __init__(self):
        self.socat_process = None
        self.serial_port = None
        self.running = False
        self.auth_id = get_computer_id()
        COMMANDS['auth'] = self.auth_id  # Set auth ID
        
    def start_socat(self):
        """Create virtual serial port pair using socat."""
        # Clean up old ports
        for port in [VIRTUAL_PORT_ARDUINO, VIRTUAL_PORT_KUMANDA]:
            if os.path.exists(port):
                os.remove(port)
        
        cmd = [
            "socat", "-d",
            f"pty,raw,echo=0,link={VIRTUAL_PORT_ARDUINO}",
            f"pty,raw,echo=0,link={VIRTUAL_PORT_KUMANDA}"
        ]
        
        self.socat_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for ports to be created
        for _ in range(20):  # 2 seconds timeout
            if os.path.exists(VIRTUAL_PORT_ARDUINO) and os.path.exists(VIRTUAL_PORT_KUMANDA):
                break
            time.sleep(0.1)
        
        if not os.path.exists(VIRTUAL_PORT_ARDUINO):
            raise RuntimeError("Failed to create virtual serial ports")
        
        log("MOCK", f"Virtual ports created", "OK")
        
    def connect(self):
        """Connect to the Arduino side of virtual port."""
        try:
            self.serial_port = serial.Serial(
                VIRTUAL_PORT_ARDUINO,
                BAUD_RATE,
                timeout=0.1
            )
            log("MOCK", f"Serial connection established", "OK")
            return True
        except serial.SerialException as e:
            log("MOCK", f"Serial connection failed: {e}", "ERROR")
            return False
    
    def send(self, data):
        """Send data to kumanda.py."""
        if self.serial_port and self.serial_port.is_open:
            message = f"{data}\n"
            self.serial_port.write(message.encode('utf-8'))
            self.serial_port.flush()
            log("MOCK", f"Sent: {data}", "CMD")
        else:
            log("MOCK", "Cannot send - not connected", "ERROR")
    
    def read_loop(self):
        """Read responses from kumanda.py (in thread)."""
        while self.running:
            if self.serial_port and self.serial_port.is_open:
                try:
                    if self.serial_port.in_waiting > 0:
                        data = self.serial_port.readline().decode('utf-8').strip()
                        if data:
                            log("MOCK", f"Received: {data}", "INFO")
                except Exception as e:
                    if self.running:
                        log("MOCK", f"Read error: {e}", "ERROR")
            time.sleep(0.05)
    
    def command_loop(self):
        """Process commands from the queue (in thread)."""
        while self.running:
            try:
                cmd = command_queue.get(timeout=0.5)
                if cmd in COMMANDS:
                    code = COMMANDS[cmd]
                    if code:
                        self.send(code)
                else:
                    log("MOCK", f"Unknown command: {cmd}", "WARN")
            except:
                pass  # Queue timeout, continue
    
    def start(self):
        """Start mock Arduino."""
        self.running = True
        self.start_socat()
        
        if not self.connect():
            return False
        
        # Start read thread
        self.read_thread = threading.Thread(target=self.read_loop, daemon=True)
        self.read_thread.start()
        
        # Start command processing thread
        self.cmd_thread = threading.Thread(target=self.command_loop, daemon=True)
        self.cmd_thread.start()
        
        # Send authentication after short delay
        time.sleep(1)
        self.send(self.auth_id)
        
        return True
    
    def stop(self):
        """Stop mock Arduino."""
        self.running = False
        
        if self.serial_port:
            self.serial_port.close()
        
        if self.socat_process:
            self.socat_process.terminate()
            self.socat_process.wait()
        
        # Clean up ports
        for port in [VIRTUAL_PORT_ARDUINO, VIRTUAL_PORT_KUMANDA]:
            if os.path.exists(port):
                try:
                    os.remove(port)
                except:
                    pass
        
        log("MOCK", "Stopped", "INFO")


# =====================================================
# KUMANDA WRAPPER
# =====================================================

def patch_serial_ports():
    """Monkey-patch serial.tools.list_ports to include virtual port."""
    import serial.tools.list_ports as list_ports
    
    original_comports = list_ports.comports
    
    FakePortInfo = namedtuple('FakePortInfo', [
        'device', 'name', 'description', 'hwid',
        'vid', 'pid', 'serial_number', 'location',
        'manufacturer', 'product', 'interface'
    ])
    
    def patched_comports(include_links=False):
        real_ports = list(original_comports(include_links))
        
        if os.path.exists(VIRTUAL_PORT_KUMANDA):
            fake_port = FakePortInfo(
                device=VIRTUAL_PORT_KUMANDA,
                name=os.path.basename(VIRTUAL_PORT_KUMANDA),
                description="Mock Arduino (CH340)",
                hwid=f"USB VID:PID={FAKE_VID:04X}:{FAKE_PID:04X}",
                vid=FAKE_VID,
                pid=FAKE_PID,
                serial_number="MOCK12345",
                location=None,
                manufacturer="Mock",
                product="Mock Arduino Uno",
                interface=None
            )
            real_ports.insert(0, fake_port)
        
        return real_ports
    
    list_ports.comports = patched_comports


def start_kumanda():
    """Start kumanda.py in a separate thread."""
    def run_kumanda():
        # Setup X display access for sudo
        display = os.environ.get('DISPLAY', ':0')
        os.environ['DISPLAY'] = display
        
        # Grant root access to X display
        try:
            subprocess.run(['xhost', '+local:root'], capture_output=True)
            log("KUMANDA", f"X display access granted (DISPLAY={display})", "OK")
        except Exception as e:
            log("KUMANDA", f"xhost warning: {e}", "WARN")
        
        patch_serial_ports()
        log("KUMANDA", "Serial port detection patched", "OK")
        
        kumanda_path = os.path.join(SCRIPT_DIR, "kumanda.py")
        
        if not os.path.exists(kumanda_path):
            log("KUMANDA", "kumanda.py not found!", "ERROR")
            return
        
        log("KUMANDA", "Starting...", "INFO")
        
        with open(kumanda_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        exec_globals = {
            '__name__': '__main__',
            '__file__': kumanda_path,
        }
        
        try:
            exec(compile(code, kumanda_path, 'exec'), exec_globals)
        except Exception as e:
            log("KUMANDA", f"Error: {e}", "ERROR")
    
    thread = threading.Thread(target=run_kumanda, daemon=True)
    thread.start()
    return thread


# =====================================================
# CAPTIVE PORTAL SERVER
# =====================================================

class PortalHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler for captive portal with command integration."""
    
    def log_message(self, format, *args):
        pass  # Suppress default logging
    
    def send_portal_page(self):
        """Send the portal HTML page."""
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
        """Send JSON response."""
        content = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(content))
        self.end_headers()
        self.wfile.write(content)
    
    def send_captive_redirect(self, location):
        """Send redirect for captive portal detection."""
        html = f'''<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="refresh" content="0;url={location}">
    <script>window.location.href="{location}";</script>
</head>
<body><h1>Redirecting...</h1></body>
</html>'''
        content = html.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', len(content))
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.end_headers()
        self.wfile.write(content)
    
    def do_GET(self):
        """Handle GET requests."""
        path = urlparse(self.path).path
        client_ip = self.client_address[0]
        portal_url = f'http://{IP_ADDR}/portal'
        
        # Captive portal detection endpoints
        captive_paths = [
            '/generate_204', '/gen_204',  # Android
            '/hotspot-detect.html', '/success.txt', '/library/test/success.html',  # iOS
            '/ncsi.txt', '/connecttest.txt', '/redirect',  # Windows
            '/canonical.html', '/kindle-wifi/wifistub.html', '/check_network_status.txt'  # Others
        ]
        
        if path in captive_paths:
            log("PORTAL", f"Device detected: {client_ip}", "INFO")
            self.send_captive_redirect(portal_url)
        elif path == '/portal' or path == '/':
            self.send_portal_page()
        else:
            self.send_captive_redirect(portal_url)
    
    def do_POST(self):
        """Handle POST requests (button clicks)."""
        path = urlparse(self.path).path
        client_ip = self.client_address[0]
        
        if path == '/command':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            
            try:
                data = json.loads(body.decode('utf-8'))
                cmd = data.get('command', 'unknown')
                code = data.get('code', 'unknown')
                
                # Log the command
                log("PORTAL", f"Button: {cmd} ({code}) from {client_ip}", "CMD")
                
                # Add command to queue for mock Arduino
                command_queue.put(cmd)
                
                self.send_json({'status': 'ok', 'command': cmd})
                
            except json.JSONDecodeError:
                self.send_json({'error': 'Invalid JSON'}, 400)
        
        # Legacy endpoint for compatibility
        elif path == '/click':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            
            try:
                data = json.loads(body.decode('utf-8'))
                button = data.get('button', 'unknown')
                log("PORTAL", f"Legacy click: Button {button} from {client_ip}", "INFO")
                self.send_json({'status': 'ok', 'button': button})
            except:
                self.send_json({'error': 'Invalid JSON'}, 400)
        else:
            self.send_json({'error': 'Not found'}, 404)


def start_portal_server():
    """Start the captive portal web server."""
    socketserver.TCPServer.allow_reuse_address = True
    
    with socketserver.TCPServer(("", PORT), PortalHandler) as httpd:
        log("PORTAL", f"Server running on http://{IP_ADDR}:{PORT}", "OK")
        try:
            httpd.serve_forever()
        except:
            pass


# =====================================================
# NETWORK SETUP (from start_hotspot.sh)
# =====================================================

def setup_hotspot():
    """Configure WiFi hotspot (requires root)."""
    
    if os.geteuid() != 0:
        log("SETUP", "Root privileges required for hotspot!", "ERROR")
        log("SETUP", "Run with: sudo python3 master.py", "ERROR")
        return False
    
    log("SETUP", "Configuring network...", "INFO")
    
    # Stop NetworkManager from managing interface
    subprocess.run(["nmcli", "device", "set", INTERFACE, "managed", "no"], 
                   capture_output=True)
    
    # Kill existing processes
    subprocess.run(["pkill", "-f", "hostapd.*hostapd.conf"], capture_output=True)
    subprocess.run(["pkill", "-f", "dnsmasq.*dnsmasq.conf"], capture_output=True)
    subprocess.run(["pkill", "-f", f"wpa_supplicant.*{INTERFACE}"], capture_output=True)
    
    time.sleep(1)
    
    # Configure interface
    subprocess.run(["ip", "link", "set", INTERFACE, "down"], capture_output=True)
    subprocess.run(["ip", "addr", "flush", "dev", INTERFACE], capture_output=True)
    subprocess.run(["ip", "addr", "add", f"{IP_ADDR}/24", "dev", INTERFACE], capture_output=True)
    subprocess.run(["ip", "link", "set", INTERFACE, "up"], capture_output=True)
    
    time.sleep(1)
    
    log("SETUP", f"Interface {INTERFACE} configured with {IP_ADDR}", "OK")
    
    # Start hostapd
    hostapd_conf = os.path.join(SCRIPT_DIR, "hostapd.conf")
    subprocess.Popen(["hostapd", hostapd_conf, "-B"], 
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    
    log("SETUP", "WiFi AP started", "OK")
    
    # Start dnsmasq
    dnsmasq_conf = os.path.join(SCRIPT_DIR, "dnsmasq.conf")
    subprocess.Popen(["dnsmasq", "-C", dnsmasq_conf],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    
    log("SETUP", "DHCP/DNS server started", "OK")
    
    # Configure iptables
    subprocess.run(["sh", "-c", "echo 1 > /proc/sys/net/ipv4/ip_forward"], 
                   capture_output=True)
    subprocess.run(["iptables", "-t", "nat", "-A", "PREROUTING", "-i", INTERFACE,
                    "-p", "tcp", "--dport", "80", "-j", "DNAT", 
                    "--to-destination", f"{IP_ADDR}:80"], capture_output=True)
    subprocess.run(["iptables", "-t", "nat", "-A", "PREROUTING", "-i", INTERFACE,
                    "-p", "tcp", "--dport", "443", "-j", "DNAT",
                    "--to-destination", f"{IP_ADDR}:80"], capture_output=True)
    subprocess.run(["iptables", "-A", "FORWARD", "-i", INTERFACE, "-j", "ACCEPT"],
                   capture_output=True)
    
    log("SETUP", "Captive portal redirect configured", "OK")
    
    return True


def cleanup_hotspot():
    """Clean up hotspot configuration."""
    log("CLEANUP", "Stopping services...", "INFO")
    
    subprocess.run(["pkill", "-f", "hostapd.*hostapd.conf"], capture_output=True)
    subprocess.run(["pkill", "-f", "dnsmasq.*dnsmasq.conf"], capture_output=True)
    
    # Remove iptables rules
    subprocess.run(["iptables", "-t", "nat", "-D", "PREROUTING", "-i", INTERFACE,
                    "-p", "tcp", "--dport", "80", "-j", "DNAT",
                    "--to-destination", f"{IP_ADDR}:80"], capture_output=True)
    subprocess.run(["iptables", "-t", "nat", "-D", "PREROUTING", "-i", INTERFACE,
                    "-p", "tcp", "--dport", "443", "-j", "DNAT",
                    "--to-destination", f"{IP_ADDR}:80"], capture_output=True)
    subprocess.run(["iptables", "-D", "FORWARD", "-i", INTERFACE, "-j", "ACCEPT"],
                   capture_output=True)
    
    # Restore NetworkManager
    subprocess.run(["nmcli", "device", "set", INTERFACE, "managed", "yes"],
                   capture_output=True)
    subprocess.run(["ip", "link", "set", INTERFACE, "down"], capture_output=True)
    subprocess.run(["ip", "addr", "flush", "dev", INTERFACE], capture_output=True)
    
    log("CLEANUP", "Hotspot stopped", "OK")


# =====================================================
# MAIN
# =====================================================

def main():
    global running
    
    print("\n" + "=" * 60)
    print("  🎮 KUMANDA MASTER CONTROL SYSTEM")
    print("=" * 60 + "\n")
    
    # Setup X display access for GUI (kumanda.py uses Tkinter)
    # This is needed when running with sudo
    if 'DISPLAY' not in os.environ:
        os.environ['DISPLAY'] = ':0'
    
    # Grant root access to X display
    try:
        result = subprocess.run(['xhost', '+local:root'], capture_output=True, text=True)
        if result.returncode == 0:
            log("MAIN", f"X display access granted", "OK")
        else:
            log("MAIN", f"xhost failed (GUI may not work): {result.stderr}", "WARN")
    except FileNotFoundError:
        log("MAIN", "xhost not found - install with: sudo apt install x11-xserver-utils", "WARN")
    except Exception as e:
        log("MAIN", f"X display setup warning: {e}", "WARN")
    
    # Check socat
    if subprocess.run(["which", "socat"], capture_output=True).returncode != 0:
        log("MAIN", "socat not installed! Run: sudo apt install socat", "ERROR")
        sys.exit(1)
    
    # Initialize mock Arduino
    mock_arduino = MockArduino()
    
    def signal_handler(sig, frame):
        global running
        running = False
        print("\n")
        log("MAIN", "Shutting down...", "INFO")
        mock_arduino.stop()
        cleanup_hotspot()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 1. Start Mock Arduino
        log("MAIN", "Starting Mock Arduino...", "INFO")
        if not mock_arduino.start():
            log("MAIN", "Failed to start Mock Arduino", "ERROR")
            sys.exit(1)
        
        time.sleep(1)
        
        # 2. Start kumanda.py (in thread)
        log("MAIN", "Starting kumanda.py...", "INFO")
        kumanda_thread = start_kumanda()
        
        time.sleep(2)
        
        # 3. Setup hotspot
        log("MAIN", "Setting up WiFi hotspot...", "INFO")
        if not setup_hotspot():
            log("MAIN", "Failed to setup hotspot (try with sudo)", "ERROR")
            mock_arduino.stop()
            sys.exit(1)
        
        # 4. Start portal server (blocking)
        log("MAIN", "Starting captive portal...", "INFO")
        print("\n" + "=" * 60)
        print("  ✅ ALL SYSTEMS READY")
        print("=" * 60)
        print(f"  WiFi SSID: CaptivePortal")
        print(f"  Portal:    http://{IP_ADDR}")
        print("=" * 60 + "\n")
        
        start_portal_server()
        
    except Exception as e:
        log("MAIN", f"Error: {e}", "ERROR")
        mock_arduino.stop()
        cleanup_hotspot()
        sys.exit(1)


if __name__ == "__main__":
    main()
