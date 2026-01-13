# Captive Portal Hotspot

Transform your Linux device into a WiFi hotspot with captive portal.

## 📁 Project Structure

```
portalProj/
├── stop.sh              # Stop hotspot and restore WiFi (run from root)
├── kumanda.py           # Your existing application
├── setup/               # Setup and documentation
│   ├── setup.sh        # Auto-setup script for new devices
│   ├── README.md       # Detailed documentation
│   ├── DEPLOY.md       # Deployment tutorial
│   └── QUICKREF.md     # Quick reference guide
└── service/             # Captive portal service files
    ├── start.sh        # Start hotspot script
    ├── server.py       # Web server (port 80)
    ├── portal.html     # Landing page
    ├── hostapd.conf    # WiFi AP configuration
    └── dnsmasq.conf    # DHCP/DNS configuration
```

## 🚀 Quick Start

### First Time Setup
```bash
cd setup
sudo ./setup.sh
```
This auto-detects your wireless interface, installs dependencies, and configures everything.

### Start Hotspot
```bash
cd service
sudo ./start.sh
```

### Stop Hotspot
```bash
# From project root
sudo ./stop.sh
```

## 📡 Connection Details

- **SSID**: CaptivePortal
- **Password**: portal123
- **Gateway**: 192.168.4.1

## 📚 Documentation

- **[setup/README.md](setup/README.md)** - Complete documentation
- **[setup/DEPLOY.md](setup/DEPLOY.md)** - Deployment tutorial for different devices
- **[setup/QUICKREF.md](setup/QUICKREF.md)** - Quick reference guide

## 🔧 Requirements

- Linux with NetworkManager
- hostapd, dnsmasq, python3, iptables (auto-installed by setup.sh)
- Wireless adapter with AP mode support

## ⚡ Common Commands

```bash
# Setup on new device
cd setup && sudo ./setup.sh

# Start hotspot
cd service && sudo ./start.sh

# Stop hotspot  
sudo ./stop.sh

# View logs
tail -f /tmp/portal-server.log
```

---

For complete deployment guide, see **[setup/DEPLOY.md](setup/DEPLOY.md)**
