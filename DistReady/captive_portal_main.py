#!/usr/bin/env python3
"""
Captive Portal Main Entry Point
Bundled executable that combines network setup + Flask server
Replaces start.sh with Python implementation
"""

import os
import sys
import subprocess
import time
import signal
import threading
from pathlib import Path

# Color codes for terminal output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color

# Global variables
VERBOSE = True
flask_process = None
hostapd_process = None
dnsmasq_process = None

def log_info(msg):
    print(f"{Colors.CYAN}[INFO]{Colors.NC} {msg}")

def log_success(msg):
    print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {msg}")

def log_warning(msg):
    print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {msg}")

def log_error(msg):
    print(f"{Colors.RED}[ERROR]{Colors.NC} {msg}")

def log_debug(msg):
    if VERBOSE:
        print(f"{Colors.BLUE}[DEBUG]{Colors.NC} {msg}")

def run_command(cmd, shell=False, check=True, capture=True):
    """Execute system command with error handling"""
    try:
        if capture:
            result = subprocess.run(
                cmd if not shell else cmd,
                shell=shell,
                capture_output=True,
                text=True,
                check=check
            )
            return result.returncode == 0, result.stdout, result.stderr
        else:
            result = subprocess.run(
                cmd if not shell else cmd,
                shell=shell,
                check=check
            )
            return result.returncode == 0, "", ""
    except subprocess.CalledProcessError as e:
        return False, e.stdout if hasattr(e, 'stdout') else "", e.stderr if hasattr(e, 'stderr') else ""
    except Exception as e:
        return False, "", str(e)

def get_executable_dir():
    """Get directory where executable is located (works for PyInstaller and dev)"""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return Path(sys.executable).parent
    else:
        # Running as script
        return Path(__file__).parent

def get_resource_path(relative_path):
    """Get absolute path to resource (works for PyInstaller and dev)"""
    if getattr(sys, 'frozen', False):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).parent
    return base_path / relative_path

def load_bash_config(config_file):
    """Parse bash config.sh and return as Python dict"""
    if not config_file.exists():
        log_error(f"Configuration file not found: {config_file}")
        sys.exit(1)
    
    log_debug(f"Loading configuration from: {config_file}")
    
    # Source the bash file and export all variables
    cmd = f'source {config_file} && env'
    success, stdout, stderr = run_command(cmd, shell=True)
    
    if not success:
        log_error("Failed to load configuration")
        sys.exit(1)
    
    config = {}
    for line in stdout.split('\n'):
        if '=' in line:
            try:
                key, value = line.split('=', 1)
                # Remove quotes if present
                value = value.strip('"').strip("'")
                config[key] = value
            except:
                pass
    
    return config

def check_root():
    """Verify script is running as root"""
    if os.geteuid() != 0:
        log_error("This script must be run as root (use sudo)")
        sys.exit(1)

def check_required_files(exec_dir):
    """Verify all required external files exist"""
    log_info("Checking required files...")
    
    required_files = {
        'config.sh': exec_dir / 'config.sh',
        'hostapd.conf': exec_dir / 'hostapd.conf',
        'dnsmasq.conf': exec_dir / 'dnsmasq.conf',
        'dlI': exec_dir / 'dlI'
    }
    
    missing = []
    for name, path in required_files.items():
        if not path.exists():
            log_error(f"{name} not found in {exec_dir}")
            missing.append(name)
        else:
            log_debug(f"✓ {name} found")
    
    if missing:
        log_error(f"Missing required files: {', '.join(missing)}")
        sys.exit(1)
    
    return required_files

def check_interface(interface):
    """Verify network interface exists"""
    log_info(f"Checking interface {interface}...")
    
    success, stdout, stderr = run_command(['ip', 'link', 'show', interface])
    
    if not success:
        log_error(f"Interface {interface} not found!")
        print(f"\n{Colors.YELLOW}Available interfaces:{Colors.NC}")
        success, stdout, _ = run_command(['ip', 'link', 'show'])
        if success:
            for line in stdout.split('\n'):
                if ':' in line and line.strip()[0].isdigit():
                    iface = line.split(':')[1].strip()
                    print(f"  - {iface}")
        print(f"\n{Colors.YELLOW}Hint:{Colors.NC} Edit config.sh and set INTERFACE to your WiFi adapter")
        sys.exit(1)
    
    log_success(f"Interface {interface} exists")

def stop_network_manager(interface):
    """Stop NetworkManager from managing the interface"""
    log_info(f"Stopping NetworkManager on {interface}...")
    log_debug(f"Running: nmcli device set {interface} managed no")
    
    success, stdout, stderr = run_command(
        ['nmcli', 'device', 'set', interface, 'managed', 'no'],
        check=False
    )
    
    if success:
        log_success(f"NetworkManager stopped managing {interface}")
    else:
        log_warning("Failed to stop NetworkManager (may not be a problem)")
    
    time.sleep(1)

def configure_interface(interface, static_ip):
    """Configure network interface with static IP"""
    log_info(f"Configuring interface {interface}...")
    
    # Bring down interface
    log_debug(f"Bringing down interface {interface}")
    success, _, stderr = run_command(['ip', 'link', 'set', interface, 'down'])
    if not success:
        log_error(f"Failed to bring down interface: {stderr}")
        sys.exit(1)
    time.sleep(1)
    
    # Flush existing addresses
    log_debug(f"Flushing existing addresses on {interface}")
    run_command(['ip', 'addr', 'flush', 'dev', interface], check=False)
    
    # Add static IP
    log_debug(f"Adding IP: {static_ip}/24 to {interface}")
    success, _, stderr = run_command(['ip', 'addr', 'add', f'{static_ip}/24', 'dev', interface])
    if not success:
        log_error(f"Failed to configure IP address: {stderr}")
        sys.exit(1)
    log_success("IP address configured")
    
    # Bring up interface
    log_debug(f"Bringing interface up")
    success, _, stderr = run_command(['ip', 'link', 'set', interface, 'up'])
    if not success:
        log_error(f"Failed to bring up interface: {stderr}")
        sys.exit(1)
    log_success("Interface is up")
    time.sleep(1)

def start_hostapd(exec_dir):
    """Start hostapd access point"""
    global hostapd_process
    
    log_info("Starting hostapd...")
    hostapd_conf = exec_dir / 'hostapd.conf'
    log_debug(f"Using config: {hostapd_conf}")
    
    # Kill existing hostapd
    log_debug("Killing any existing hostapd processes")
    run_command(['killall', 'hostapd'], check=False)
    time.sleep(1)
    
    # Start hostapd in background
    log_debug(f"Running: hostapd -B {hostapd_conf}")
    with open('/tmp/hostapd.log', 'w') as log_file:
        hostapd_process = subprocess.Popen(
            ['hostapd', '-B', str(hostapd_conf)],
            stdout=log_file,
            stderr=subprocess.STDOUT
        )
    
    time.sleep(2)
    
    # Check if hostapd is running
    success, stdout, _ = run_command(['pgrep', '-x', 'hostapd'])
    if success and stdout.strip():
        log_success(f"hostapd started (PID: {stdout.strip()})")
    else:
        log_error("hostapd process not found after start")
        print(f"\n{Colors.YELLOW}hostapd.log contents:{Colors.NC}")
        try:
            with open('/tmp/hostapd.log', 'r') as f:
                print(f.read())
        except:
            pass
        sys.exit(1)

def start_dnsmasq(exec_dir):
    """Start dnsmasq DNS/DHCP server"""
    global dnsmasq_process
    
    log_info("Starting dnsmasq...")
    dnsmasq_conf = exec_dir / 'dnsmasq.conf'
    log_debug(f"Using config: {dnsmasq_conf}")
    
    # Kill existing dnsmasq
    log_debug("Killing any existing dnsmasq processes")
    run_command(['killall', 'dnsmasq'], check=False)
    time.sleep(1)
    
    # Start dnsmasq
    log_debug(f"Running: dnsmasq -C {dnsmasq_conf}")
    
    # Remove old log and create new writable one
    try:
        os.remove('/tmp/dnsmasq.log')
    except:
        pass
    Path('/tmp/dnsmasq.log').touch(mode=0o666)
    
    success, stdout, stderr = run_command([
        'dnsmasq', '-C', str(dnsmasq_conf),
        '--log-facility=/tmp/dnsmasq.log'
    ], check=False)
    
    time.sleep(1)
    
    # Check if dnsmasq is running
    check_success, pid_out, _ = run_command(['pgrep', '-x', 'dnsmasq'])
    if check_success and pid_out.strip():
        log_success(f"dnsmasq started (PID: {pid_out.strip()})")
    else:
        log_error("dnsmasq process not found after start")
        print(f"\n{Colors.YELLOW}dnsmasq error output:{Colors.NC}")
        if stderr:
            print(stderr)
        sys.exit(1)

def configure_iptables(interface, static_ip, server_port):
    """Configure iptables for captive portal"""
    log_info("Configuring iptables...")
    
    # Clean up old rules
    log_debug("Removing old captive portal rules (if any)")
    old_rules = [
        ['iptables', '-t', 'nat', '-D', 'PREROUTING', '-i', interface, '-p', 'tcp', '--dport', '80', '-j', 'DNAT', '--to-destination', f'{static_ip}:{server_port}'],
        ['iptables', '-t', 'nat', '-D', 'PREROUTING', '-i', interface, '-p', 'tcp', '--dport', '443', '-j', 'DNAT', '--to-destination', f'{static_ip}:{server_port}'],
        ['iptables', '-D', 'INPUT', '-i', interface, '-p', 'tcp', '--dport', '80', '-j', 'ACCEPT'],
        ['iptables', '-D', 'INPUT', '-i', interface, '-p', 'udp', '--dport', '443', '-j', 'REJECT'],
        ['iptables', '-D', 'INPUT', '-i', interface, '-p', 'udp', '--dport', '443', '-j', 'REJECT', '--reject-with', 'icmp-port-unreachable'],
        ['iptables', '-D', 'INPUT', '-i', interface, '-p', 'tcp', '--dport', '443', '-j', 'REJECT'],
        ['iptables', '-D', 'INPUT', '-i', interface, '-p', 'tcp', '--dport', '443', '-j', 'REJECT', '--reject-with', 'tcp-reset'],
        ['iptables', '-D', 'FORWARD', '-i', interface, '-p', 'udp', '--dport', '443', '-j', 'REJECT'],
        ['iptables', '-D', 'INPUT', '-i', interface, '-j', 'ACCEPT'],
        ['iptables', '-D', 'OUTPUT', '-o', interface, '-j', 'ACCEPT'],
    ]
    
    for rule in old_rules:
        run_command(rule, check=False)
    
    # Add high-priority DNS rules
    log_debug("Adding high-priority DNS rule (critical for captive portal)")
    run_command(['iptables', '-I', 'INPUT', '-i', interface, '-p', 'udp', '--dport', '53', '-j', 'ACCEPT'])
    run_command(['iptables', '-I', 'INPUT', '-i', interface, '-p', 'tcp', '--dport', '53', '-j', 'ACCEPT'])
    
    # Block QUIC protocol
    log_debug("Blocking QUIC protocol (UDP 443)")
    run_command(['iptables', '-A', 'INPUT', '-i', interface, '-p', 'udp', '--dport', '443', '-j', 'REJECT'])
    
    # Add NAT rule for HTTP redirect
    log_debug("Adding NAT rule for HTTP redirect")
    run_command(['iptables', '-t', 'nat', '-A', 'PREROUTING', '-i', interface, '-p', 'tcp', '--dport', '80', '-j', 'DNAT', '--to-destination', f'{static_ip}:{server_port}'])
    
    # Add INPUT/OUTPUT rules
    log_debug("Adding INPUT/OUTPUT rules")
    run_command(['iptables', '-A', 'INPUT', '-i', interface, '-j', 'ACCEPT'])
    run_command(['iptables', '-A', 'OUTPUT', '-o', interface, '-j', 'ACCEPT'])
    
    log_success("iptables configured")

def start_flask_server(exec_dir, config):
    """Start Flask web server"""
    global flask_process
    
    log_info("Starting web server...")
    
    # Set environment variables for the server
    env = os.environ.copy()
    if 'DISPLAY' not in env:
        env['DISPLAY'] = ':0'
        log_debug("Forced DISPLAY=:0 for GUI applications")
    
    # Import and start server
    server_port = config.get('SERVER_PORT', '80')
    
    log_debug(f"Running: python3 server.py --port {server_port}")
    
    # Start server in background
    flask_process = subprocess.Popen(
        [sys.executable, str(exec_dir / 'server.py'), '--port', server_port],
        stdout=open('/tmp/portal-server.log', 'w'),
        stderr=subprocess.STDOUT,
        env=env,
        cwd=str(exec_dir)
    )
    
    # Save PID
    with open('/tmp/portal-server.pid', 'w') as f:
        f.write(str(flask_process.pid))
    
    log_debug(f"Server started with PID: {flask_process.pid}")
    time.sleep(2)
    
    # Check if server is running
    if flask_process.poll() is None:
        log_success(f"Web server is running (PID: {flask_process.pid})")
        
        # Check if listening on port
        success, stdout, _ = run_command(['ss', '-tuln'], check=False)
        if success and f':{server_port}' in stdout:
            log_success(f"Server is listening on port {server_port}")
    else:
        log_error("Web server failed to start")
        print(f"\n{Colors.YELLOW}Server log contents:{Colors.NC}")
        try:
            with open('/tmp/portal-server.log', 'r') as f:
                print(f.read())
        except:
            pass
        sys.exit(1)

def grant_display_permission():
    """Grant X11 display permission for root"""
    if 'SUDO_USER' in os.environ:
        sudo_user = os.environ['SUDO_USER']
        log_info(f"Granting X11 display permission for root (via {sudo_user})...")
        run_command(
            ['sudo', '-u', sudo_user, 'env', 'DISPLAY=:0', 'xhost', '+local:root'],
            check=False
        )
    else:
        os.environ['DISPLAY'] = ':0'
        run_command(['xhost', '+local:root'], check=False)

def cleanup(interface):
    """Cleanup function called on exit"""
    global flask_process, hostapd_process, dnsmasq_process
    
    print(f"\n{Colors.YELLOW}Shutting down captive portal...{Colors.NC}")
    
    # Stop Flask server
    if flask_process:
        flask_process.terminate()
        try:
            flask_process.wait(timeout=5)
        except:
            flask_process.kill()
    
    # Stop dnsmasq
    run_command(['killall', 'dnsmasq'], check=False)
    
    # Stop hostapd
    run_command(['killall', 'hostapd'], check=False)
    
    # Clear iptables
    run_command(['iptables', '-t', 'nat', '-F'], check=False)
    
    # Re-enable NetworkManager
    if interface:
        run_command(['nmcli', 'device', 'set', interface, 'managed', 'yes'], check=False)
    
    log_success("Captive portal stopped")

def main():
    global VERBOSE
    
    # Get executable directory
    exec_dir = get_executable_dir()
    
    # Print header
    print(f"\n{Colors.GREEN}=== Starting Captive Portal Hotspot ==={Colors.NC}\n")
    
    # Check root
    check_root()
    
    # Check required files
    files = check_required_files(exec_dir)
    
    # Load configuration
    config = load_bash_config(files['config.sh'])
    
    # Extract configuration
    interface = config.get('INTERFACE', 'wlan0')
    static_ip = config.get('STATIC_IP', '192.168.4.1')
    ssid = config.get('SSID', 'CaptivePortal')
    wpa_pass = config.get('WPA_PASSPHRASE', 'portal123')
    server_port = config.get('SERVER_PORT', '80')
    
    # Display configuration
    print(f"{Colors.CYAN}Configuration:{Colors.NC}")
    print(f"  Interface:    {Colors.YELLOW}{interface}{Colors.NC}")
    print(f"  Static IP:    {Colors.YELLOW}{static_ip}{Colors.NC}")
    print(f"  SSID:         {Colors.YELLOW}{ssid}{Colors.NC}")
    print(f"  Server Port:  {Colors.YELLOW}{server_port}{Colors.NC}")
    print()
    
    # Grant display permission
    grant_display_permission()
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        cleanup(interface)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Execute setup steps
        check_interface(interface)
        stop_network_manager(interface)
        configure_interface(interface, static_ip)
        start_hostapd(exec_dir)
        start_dnsmasq(exec_dir)
        configure_iptables(interface, static_ip, server_port)
        start_flask_server(exec_dir, config)
        
        # Success message
        print(f"\n{Colors.GREEN}✓ Captive Portal Hotspot is running!{Colors.NC}\n")
        print("━" * 60)
        print(f"{Colors.CYAN}Network Information:{Colors.NC}")
        print(f"  SSID:        {Colors.GREEN}{ssid}{Colors.NC}")
        print(f"  Password:    {Colors.GREEN}{wpa_pass}{Colors.NC}")
        print(f"  Gateway IP:  {Colors.GREEN}{static_ip}{Colors.NC}")
        print(f"  Interface:   {Colors.GREEN}{interface}{Colors.NC}")
        print("━" * 60)
        print(f"\n{Colors.GREEN}✓{Colors.NC} Clients will be redirected to the captive portal page automatically.")
        print(f"\nPress Ctrl+C to stop")
        print()
        
        # Keep running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        cleanup(interface)
    except Exception as e:
        log_error(f"Unexpected error: {e}")
        cleanup(interface)
        sys.exit(1)

if __name__ == "__main__":
    main()
