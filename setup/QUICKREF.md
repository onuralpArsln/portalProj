# Quick Reference Guide

## 🎯 Common Commands

### New Device Setup
```bash
sudo ./setup.sh          # Auto-configure everything
```

### Daily Operations
```bash
sudo ./start.sh          # Start hotspot
sudo ./stop.sh           # Stop hotspot
```

### Check Status
```bash
ps aux | grep -E "hostapd|dnsmasq"     # Check running services
ip addr show wlan0                      # Check IP configuration
tail -f /tmp/portal-server.log          # Monitor connections
```

---

## 📝 Quick Customization

### Change Network Name
```bash
nano hostapd.conf
# Edit: ssid=YourNetworkName
```

### Change Password
```bash
nano hostapd.conf
# Edit: wpa_passphrase=YourPassword
```

### Change IP Range
```bash
nano dnsmasq.conf
# Edit: dhcp-range=192.168.4.2,192.168.4.50,...
```

---

## 🔧 Troubleshooting Commands

### Wireless Interface Issues
```bash
ip link show | grep w                   # Find wireless interface
iw list | grep "AP"                     # Check AP mode support
```

### Service Conflicts
```bash
sudo systemctl stop hostapd dnsmasq     # Stop system services
sudo systemctl disable hostapd dnsmasq  # Disable on boot
```

### Manual WiFi Restore
```bash
sudo nmcli device set wlan0 managed yes
sudo systemctl restart NetworkManager
```

### Check Logs
```bash
cat /tmp/hostapd.log                    # hostapd errors
cat /tmp/dnsmasq.log                    # DHCP/DNS issues
cat /tmp/portal-server.log              # Web server requests
```

---

## 📱 Connection Info

**SSID:** CaptivePortal  
**Password:** portal123  
**Gateway:** 192.168.4.1  
**DHCP Range:** 192.168.4.2 - 192.168.4.20

---

## 🚀 Deployment to New Device

**Method 1 - Git:**
```bash
git clone <repo-url> captive-portal && cd captive-portal
sudo ./setup.sh && sudo ./start.sh
```

**Method 2 - SCP:**
```bash
# From source machine:
tar -czf cp.tar.gz *.sh *.py *.html *.conf
scp cp.tar.gz user@target:~/

# On target machine:
tar -xzf cp.tar.gz && sudo ./setup.sh && sudo ./start.sh
```

---

## 📚 File Overview

| File | Purpose |
|------|---------|
| `setup.sh` | First-time setup & dependency installation |
| `start.sh` | Start the captive portal |
| `stop.sh` | Stop & restore WiFi |
| `server.py` | Web server (port 80) |
| `portal.html` | Landing page |
| `hostapd.conf` | WiFi AP config |
| `dnsmasq.conf` | DHCP/DNS config |

---

## ⚠️ Common Issues

**"hostapd: command not found"**
→ Run `sudo ./setup.sh` to install dependencies

**"Interface busy"**
→ Run `sudo ./stop.sh` first, then `sudo ./start.sh`

**"Can't restore WiFi"**
→ Run `sudo nmcli device set wlan0 managed yes`

**Portal doesn't appear on phone**
→ Visit any HTTP website (not HTTPS) in browser

---

See **[DEPLOY.md](DEPLOY.md)** for complete deployment guide  
See **[README.md](README.md)** for detailed documentation
