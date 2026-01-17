#!/usr/bin/env python3
import os
import sys
import subprocess
import time
import signal
import psutil
import socket
import config_loader
import server
import server_display  # Server-side on-screen notifications


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

def is_port_available(port, host='0.0.0.0'):
    """Check if port is available for binding"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        sock.close()
        return True
    except OSError:
        return False

def get_processes_using_port(port):
    """Find all processes using the specified port"""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            connections = proc.connections(kind='inet')
            for conn in connections:
                if conn.status == 'LISTEN' and conn.laddr.port == port:
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cmdline': ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                    })
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
            continue
    return processes

def kill_process_by_pid(pid, process_name, timeout=5):
    """Kill a process by PID with graceful fallback"""
    try:
        proc = psutil.Process(pid)
        log_info(f"  Sending SIGTERM to {process_name} (PID: {pid})...")
        proc.terminate()
        try:
            proc.wait(timeout=timeout)
            log_success(f"  Process {pid} terminated gracefully")
            return True
        except psutil.TimeoutExpired:
            log_warning(f"  Process {pid} didn't respond, sending SIGKILL...")
            proc.kill()
            proc.wait(timeout=3)
            log_success(f"  Process {pid} killed forcefully")
            return True
    except psutil.NoSuchProcess:
        return True
    except psutil.AccessDenied:
        log_error(f"  No permission to kill process {pid}")
        return False
    except Exception as e:
        log_error(f"  Error killing process {pid}: {e}")
        return False

def cleanup_port(port, host='0.0.0.0', max_retries=3):
    """Clean up processes using the port"""
    log_info(f"Checking port {port} availability...")
    
    for attempt in range(max_retries):
        if is_port_available(port, host):
            log_success(f"Port {port} is available")
            return True
        
        processes = get_processes_using_port(port)
        
        if not processes:
            log_warning(f"Port {port} appears busy but no processes found")
            time.sleep(1)
            continue
        
        log_warning(f"Found {len(processes)} process(es) using port {port}:")
        for proc in processes:
            log_info(f"  - PID {proc['pid']}: {proc['name']}")
            if proc['cmdline']:
                log_info(f"    Command: {proc['cmdline'][:80]}...")
        
        success_count = 0
        for proc in processes:
            if kill_process_by_pid(proc['pid'], proc['name']):
                success_count += 1
        
        time.sleep(1)
    
    if is_port_available(port, host):
        log_success(f"Port {port} successfully cleaned up")
        return True
    else:
        log_error(f"Failed to free port {port} after {max_retries} attempts")
        return False

def setup_audio_environment():
    """
    Setup audio environment for PulseAudio/PipeWire
    Detects user and configures audio environment variables
    Equivalent to start.sh lines 58-106
    """
    sudo_user = os.environ.get("SUDO_USER")
    sudo_uid = os.environ.get("SUDO_UID")
    
    if not sudo_user:
        # Fallback detection
        log_warning("SUDO_USER not set, attempting fallback detection...")
        try:
            # Try 'who' command
            who_output = run_cmd("who", capture=True)
            if who_output:
                sudo_user = who_output.split()[0]
                sudo_uid = run_cmd(f"id -u {sudo_user}", capture=True)
                log_warning(f"Detected user via 'who': {sudo_user} (UID: {sudo_uid})")
        except:
            log_warning("Could not detect user, using defaults")
            sudo_user = "root"
            sudo_uid = "0"
    
    if not sudo_uid:
        # Calculate UID if not available
        sudo_uid = run_cmd(f"id -u {sudo_user}", capture=True)
    
    # Get user's home directory
    try:
        user_home = os.path.expanduser(f"~{sudo_user}")
    except:
        user_home = f"/home/{sudo_user}"
    
    # Set audio environment variables
    log_info(f"Configuring audio environment for user: {sudo_user}")
    
    os.environ["XDG_RUNTIME_DIR"] = f"/run/user/{sudo_uid}"
    os.environ["PULSE_RUNTIME_PATH"] = f"/run/user/{sudo_uid}/pulse"
    os.environ["PULSE_COOKIE"] = f"{user_home}/.config/pulse/cookie"
    os.environ["PULSE_SERVER"] = f"unix:/run/user/{sudo_uid}/pulse/native"
    
    log_info(f"  User: {sudo_user} (UID: {sudo_uid})")
    log_info(f"  XDG_RUNTIME_DIR: /run/user/{sudo_uid}")
    log_info(f"  PULSE_COOKIE: {user_home}/.config/pulse/cookie")
    
    # Validate paths (warnings only, don't fail)
    runtime_dir = f"/run/user/{sudo_uid}"
    pulse_cookie = f"{user_home}/.config/pulse/cookie"
    
    if not os.path.isdir(runtime_dir):
        log_warning(f"Runtime directory not found: {runtime_dir}")
        log_warning(f"User {sudo_user} may not be logged in")
    
    if not os.path.isfile(pulse_cookie):
        log_warning(f"PulseAudio cookie not found: {pulse_cookie}")
        log_warning("Audio may not work properly")
    
    return sudo_user  # Return for use in setup_x11

def setup_x11():
    """
    Setup X11 display permission and audio environment
    """
    # First setup audio environment
    sudo_user = setup_audio_environment()
    
    # Then setup X11
    if sudo_user and sudo_user != "root":
        log_info(f"Granting X11 display permission for root (via {sudo_user})...")
        run_cmd(f"sudo -u {sudo_user} env DISPLAY=:0 xhost +local:root > /dev/null 2>&1", check=False)
    else:
        os.environ["DISPLAY"] = ":0"
        run_cmd("xhost +local:root > /dev/null 2>&1", check=False)
def cleanup_all(iface, port):
    """
    Comprehensive cleanup before starting services
    Equivalent to start.sh lines 96-145
    """
    log_info("=" * 60)
    log_info("CLEANUP SECTION - Stopping existing services")
    log_info("=" * 60)
    
    # Step 1: Stop Python web server
    log_info("Step 1/5: Stopping Python web server...")
    run_cmd("pkill -f 'python3 server.py'", check=False)
    run_cmd("pkill -f 'server.py'", check=False)
    
    pid_file = "/tmp/portal-server.pid"
    if os.path.exists(pid_file):
        try:
            with open(pid_file, 'r') as f:
                pid = f.read().strip()
            run_cmd(f"kill {pid}", check=False)
            os.remove(pid_file)
            log_success(f"Removed PID file: {pid_file}")
        except:
            pass
    
    log_success("Python web server stopped")
    time.sleep(1)
    
    # Step 2: Stop dnsmasq
    log_info("Step 2/5: Stopping dnsmasq...")
    run_cmd("killall dnsmasq", check=False)
    run_cmd("pkill -f dnsmasq", check=False)
    log_success("dnsmasq stopped")
    time.sleep(1)
    
    # Step 3: Stop hostapd
    log_info("Step 3/5: Stopping hostapd...")
    run_cmd("killall hostapd", check=False)
    run_cmd("pkill -f hostapd", check=False)
    log_success("hostapd stopped")
    time.sleep(1)
    
    # Step 4: Clear iptables rules
    log_info("Step 4/5: Clearing iptables rules...")
    run_cmd("iptables -F", check=False)
    run_cmd("iptables -t nat -F", check=False)
    run_cmd("iptables -t mangle -F", check=False)
    run_cmd("iptables -X", check=False)
    run_cmd("iptables -t nat -X", check=False)
    run_cmd("iptables -t mangle -X", check=False)
    run_cmd("iptables -P INPUT ACCEPT", check=False)
    run_cmd("iptables -P FORWARD ACCEPT", check=False)
    run_cmd("iptables -P OUTPUT ACCEPT", check=False)
    log_success("iptables rules cleared")
    time.sleep(1)
    
    # Step 5: Reset network interface
    log_info(f"Step 5/5: Resetting network interface {iface}...")
    run_cmd(f"ip addr flush dev {iface}", check=False)
    run_cmd(f"ip link set {iface} down", check=False)
    run_cmd(f"nmcli device set {iface} managed yes", check=False)
    log_success(f"Interface {iface} reset")
    time.sleep(1)
    
    log_info("=" * 60)
    log_success("CLEANUP COMPLETE - Ready to start fresh")
    log_info("=" * 60)

def start_services():
    if os.geteuid() != 0:
        log_error("This script must be run as root (use sudo)")

    config = config_loader.load_config()
    iface = config.get('INTERFACE')
    ip = config.get('STATIC_IP')
    port = config.get('SERVER_PORT', '8080')
    base_dir = "/home/hp"  # Fixed absolute path for configs
    
    log_info(f"Starting Captive Portal on {iface} ({ip})...")

    # Cleanup all existing services first

    cleanup_all(iface, port)

    # Grant X11 and setup audio
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

    # 6. Clean up port before starting server
    log_info(f"Cleaning up port {port}...")
    if not cleanup_port(int(port), ip):
        log_error(f"Cannot free port {port}, aborting server start")
        log_error("Please check what's using the port: sudo lsof -i :{port}")
        sys.exit(1)

    # 7. Start Web Server
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
        
        # 2. Clear iptables rules (Full cleanup matching cleanup_all)
        log_info("Clearing iptables rules...")
        run_cmd("iptables -F", check=False)
        run_cmd("iptables -t nat -F", check=False)
        run_cmd("iptables -t mangle -F", check=False)
        run_cmd("iptables -X", check=False)
        run_cmd("iptables -t nat -X", check=False)
        run_cmd("iptables -t mangle -X", check=False)
        run_cmd("iptables -P INPUT ACCEPT", check=False)
        run_cmd("iptables -P FORWARD ACCEPT", check=False)
        run_cmd("iptables -P OUTPUT ACCEPT", check=False)
        
        # 3. Reset interface
        log_info(f"Resetting interface {iface}...")
        run_cmd(f"ip addr flush dev {iface}", check=False)
        run_cmd(f"ip link set {iface} down", check=False)
        
        # 4. Restore NetworkManager management (No restart!)
        log_info("Restoring NetworkManager management...")
        run_cmd(f"nmcli device set {iface} managed yes", check=False)
        # run_cmd("systemctl restart NetworkManager", check=False) # REMOVED: Causes race condition
        
        log_success("Cleanup complete. Networking restored.")
    except Exception as e:
        log_error(f"Error during cleanup: {e}")
    finally:
        sys.exit(0)

if __name__ == "__main__":
    # Write launch time to log immediately
    try:
        log_path = os.path.join(get_executable_dir(), "launchlog.txt")
        with open(log_path, "a") as f:
            f.write(f"Launcher started at: {time.ctime()}\n")
            # Force flush to ensure it's written even if we crash immediately
            f.flush()
            os.fsync(f.fileno())
    except Exception as e:
        print(f"Failed to write launch log: {e}")
    
    a=10
    for i in range(10):
        a*=a
        time.sleep(1)

    server_display.show_notification("Merhaba")
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    start_services()
