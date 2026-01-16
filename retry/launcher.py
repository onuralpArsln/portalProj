#!/usr/bin/env python3
import os
import sys
import subprocess
import time
import signal
import psutil
import config_loader
import server

# Colors for output
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
CYAN = '\033[0;36m'
NC = '\033[0m'

def log_info(msg): print(f"{CYAN}[INFO]{NC} {msg}")
def log_success(msg): print(f"{GREEN}[SUCCESS]{NC} {msg}")
def log_warning(msg): print(f"{YELLOW}[WARNING]{NC} {msg}")
def log_error(msg): print(f"{RED}[ERROR]{NC} {msg}")

def get_executable_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def run_cmd(cmd, check=True, capture=False):
    try:
        if capture:
            result = subprocess.run(cmd, shell=True, check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return result.stdout.strip()
        else:
            subprocess.run(cmd, shell=True, check=check)
            return True
    except subprocess.CalledProcessError as e:
        log_error(f"Command failed: {cmd}")
        if capture: return e.stderr.strip()
        return False

def setup_x11():
    sudo_user = os.environ.get("SUDO_USER")
    if sudo_user:
        log_info(f"Granting X11 display permission for root (via {sudo_user})...")
        run_cmd(f"sudo -u {sudo_user} env DISPLAY=:0 xhost +local:root >/dev/null 2>&1", check=False)
    else:
        os.environ["DISPLAY"] = ":0"
        run_cmd("xhost +local:root >/dev/null 2>&1", check=False)

def start_services():
    if os.geteuid() != 0:
        log_error("This script must be run as root (use sudo)")

    config = config_loader.load_config()
    iface = config.get('INTERFACE')
    ip = config.get('STATIC_IP')
    port = config.get('SERVER_PORT', '8080')
    base_dir = "/home/hp"  # Fixed absolute path for configs
    
    log_info(f"Starting Captive Portal on {iface} ({ip})...")

    # Grant X11
    setup_x11()

    # Required files check
    for f in ["hostapd.conf", "dnsmasq.conf"]:
        if not os.path.exists(os.path.join(base_dir, f)):
            log_error(f"{f} not found in {base_dir}")
            # We don't exit(1) because we want to allow manual recovery if needed
            # but for services it is critical. Let's keep a warning.

    # 1. NM stop
    log_info(f"Stopping NetworkManager on {iface}...")
    run_cmd(f"nmcli device set {iface} managed no", check=False)
    
    # 2. Interface setup
    log_info(f"Configuring interface {iface}...")
    run_cmd(f"ip link set {iface} down", check=False)
    run_cmd(f"ip addr flush dev {iface}", check=False)
    run_cmd(f"ip addr add {ip}/24 dev {iface}")
    run_cmd(f"ip link set {iface} up")
    
    # 3. Hostapd
    log_info("Starting hostapd...")
    run_cmd("killall hostapd 2>/dev/null", check=False)
    subprocess.Popen(["hostapd", "-B", os.path.join(base_dir, "hostapd.conf")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    
    # 4. Dnsmasq
    log_info("Starting dnsmasq...")
    run_cmd("killall dnsmasq 2>/dev/null", check=False)
    subprocess.Popen(["dnsmasq", "-C", os.path.join(base_dir, "dnsmasq.conf")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # 5. Iptables
    log_info("Configuring iptables...")
    # Clean old rules
    run_cmd(f"iptables -t nat -D PREROUTING -i {iface} -p tcp --dport 80 -j DNAT --to-destination {ip}:{port} 2>/dev/null", check=False)
    run_cmd(f"iptables -t nat -D PREROUTING -i {iface} -p tcp --dport 443 -j DNAT --to-destination {ip}:{port} 2>/dev/null", check=False)
    run_cmd(f"iptables -D INPUT -i {iface} -j ACCEPT 2>/dev/null", check=False)
    
    # Add new
    run_cmd(f"iptables -t nat -A PREROUTING -i {iface} -p tcp --dport 80 -j DNAT --to-destination {ip}:{port}")
    run_cmd(f"iptables -t nat -A PREROUTING -i {iface} -p tcp --dport 443 -j DNAT --to-destination {ip}:{port}")
    run_cmd(f"iptables -A INPUT -i {iface} -j ACCEPT")

    # 6. Start Web Server
    log_success("Captive Portal is ready!")
    log_info(f"SSID: {config.get('SSID')}")
    
    # Initialize server (License check, Display, etc.)
    server.init_server()
    
    # Run the Flask app
    server.app.run(host=ip, port=int(port), debug=False)

def cleanup(sig, frame):
    log_info("\nStopping Captive Portal...")
    try:
        config = config_loader.load_config()
        iface = config.get('INTERFACE')
        
        # 1. Stop networking services
        log_info("Stopping hostapd and dnsmasq...")
        run_cmd("killall hostapd 2>/dev/null", check=False)
        run_cmd("killall dnsmasq 2>/dev/null", check=False)
        
        # 2. Clear iptables rules
        log_info("Clearing iptables rules...")
        run_cmd("iptables -F", check=False)
        run_cmd("iptables -t nat -F", check=False)
        
        # 3. Reset interface
        log_info(f"Resetting interface {iface}...")
        run_cmd(f"ip addr flush dev {iface}", check=False)
        run_cmd(f"ip link set {iface} down", check=False)
        
        # 4. Restore NetworkManager
        log_info("Restoring NetworkManager management...")
        run_cmd(f"nmcli device set {iface} managed yes", check=False)
        run_cmd("systemctl restart NetworkManager", check=False)
        
        log_success("Cleanup complete. Networking restored.")
    except Exception as e:
        log_error(f"Error during cleanup: {e}")
    finally:
        sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    start_services()
