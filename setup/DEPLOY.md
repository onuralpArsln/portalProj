# Captive Portal Deployment Tutorial

Complete guide for deploying the captive portal hotspot system on different Linux devices.

---

## 📋 Prerequisites

### Supported Systems
- **Linux distributions**: Debian, Ubuntu, Mint, Kali, Arch, Fedora, etc.
- **Requirements**:
  - Wireless network adapter capable of AP mode
  - Root/sudo access
  - NetworkManager (recommended for easy WiFi restoration)

### Check Your Wireless Adapter

```bash
# List wireless interfaces
ip link show | grep -E "^[0-9]+: w"

# Check if interface supports AP mode
iw list | grep -A 10 "Supported interface modes" | grep "AP"
```

If you see "* AP" in the output, your adapter supports access point mode. ✅

---

## 🚀 Quick Deployment (New Device)

### Method 1: Clone from Git Repository

```bash
# Clone the repository
git clone <your-repo-url> captive-portal
cd captive-portal

# Run setup script
sudo ./setup.sh

# Start the hotspot
sudo ./start.sh
```

### Method 2: Manual File Transfer

1. **Copy files to the target device:**
   ```bash
   # On your current machine, create archive
   cd /home/onuralp/project/portalProj
   tar -czf captive-portal.tar.gz *.sh *.py *.html *.conf README.md

   # Transfer to target device (replace user@target-ip)
   scp captive-portal.tar.gz user@target-ip:~/
   ```

2. **On the target device:**
   ```bash
   # Extract files
   tar -xzf captive-portal.tar.gz
   cd captive-portal

   # Run setup
   sudo ./setup.sh

   # Start hotspot
   sudo ./start.sh
   ```

---

## 🔧 setup.sh - Automated Configuration

The `setup.sh` script automates the entire setup process:

### What It Does

1. ✅ **Detects wireless interface** automatically
2. ✅ **Checks for required packages**:
   - hostapd
   - dnsmasq
   - python3
   - iptables
   - NetworkManager
3. ✅ **Installs missing packages** (works with apt, yum, pacman)
4. ✅ **Updates configuration files** with detected interface
5. ✅ **Verifies all project files** are present
6. ✅ **Sets correct permissions** on scripts

### Usage

```bash
sudo ./setup.sh
```

### Expected Output

```
=====================================
  Captive Portal Hotspot Setup
=====================================

[1/6] Detecting wireless interface...
  ✓ Found wireless interface: wlan0

[2/6] Checking required packages...
  ✓ hostapd installed
  ✓ dnsmasq installed
  ✓ python3 installed
  ✓ NetworkManager installed
  ✓ iptables installed

[3/6] All required packages are installed

[4/6] Updating configuration files...
  ✓ hostapd.conf already configured for wlan0
  ✓ dnsmasq.conf already configured for wlan0
  ✓ Updated start.sh interface to wlan0
  ✓ Updated stop.sh interface to wlan0

[5/6] Verifying project files...
  ✓ hostapd.conf
  ✓ dnsmasq.conf
  ✓ start.sh
  ✓ stop.sh
  ✓ server.py
  ✓ portal.html

[6/6] Setting script permissions...
  ✓ Scripts are executable

=====================================
✓ Setup Complete!
=====================================

Configuration Summary:
  Wireless Interface: wlan0
  SSID: CaptivePortal
  Password: portal123
  Gateway IP: 192.168.4.1
```

---

## 📦 Manual Installation (Without setup.sh)

If you prefer to install manually:

### Step 1: Install Dependencies

**Debian/Ubuntu:**
```bash
sudo apt-get update
sudo apt-get install -y hostapd dnsmasq python3 iptables
```

**Arch Linux:**
```bash
sudo pacman -Sy hostapd dnsmasq python iptables
```

**Fedora/RHEL:**
```bash
sudo yum install -y hostapd dnsmasq python3 iptables
```

### Step 2: Detect Your Wireless Interface

```bash
ip link show | grep -E "^[0-9]+: w" | awk -F': ' '{print $2}'
```

### Step 3: Update Configuration Files

Edit the following files and replace the interface name:

**hostapd.conf:**
```bash
# Change this line to your interface
interface=wlan0
```

**dnsmasq.conf:**
```bash
# Change this line to your interface
interface=wlan0
```

**start.sh:**
```bash
# Change this line to your interface
INTERFACE="wlan0"
```

**stop.sh:**
```bash
# Change this line to your interface
INTERFACE="wlan0"
```

### Step 4: Make Scripts Executable

```bash
chmod +x setup.sh start.sh stop.sh server.py
```

---

## 🎯 Customization

### Change WiFi Network Name (SSID)

Edit `hostapd.conf`:
```conf
ssid=YourNetworkName
```

### Change WiFi Password

Edit `hostapd.conf`:
```conf
wpa_passphrase=YourPassword123
```

### Make Open Network (No Password)

Edit `hostapd.conf`, remove or comment out these lines:
```conf
# wpa=2
# wpa_passphrase=portal123
# wpa_key_mgmt=WPA-PSK
# wpa_pairwise=TKIP
# rsn_pairwise=CCMP
```

### Change IP Address Range

Edit `dnsmasq.conf`:
```conf
# Change the DHCP range
dhcp-range=192.168.4.2,192.168.4.50,255.255.255.0,24h

# Change the gateway
dhcp-option=3,192.168.4.1
dhcp-option=6,192.168.4.1
address=/#/192.168.4.1
```

Also update `start.sh`:
```bash
STATIC_IP="192.168.4.1"
```

### Customize Portal Page

Edit `portal.html` to:
- Add your branding/logo
- Change colors and styling
- Add terms of service
- Display custom messages

---

## 🔍 Troubleshooting by Device

### Raspberry Pi

**Issue:** Interface is named differently (wlan0, wlan1)
```bash
# Run setup.sh to auto-detect
sudo ./setup.sh
```

**Issue:** WiFi power management interferes
```bash
# Disable power management
sudo iw dev wlan0 set power_save off
```

### Linux Laptop

**Issue:** Cannot start while connected to WiFi
```bash
# Disconnect from WiFi first
nmcli device disconnect wlan0
# Then run start.sh
sudo ./start.sh
```

### Virtual Machines

**Note:** Most VMs don't support WiFi AP mode. Use a USB WiFi adapter with:
- Passthrough to VM enabled
- AP mode support

### Different Distributions

**Arch/Manjaro:**
- May need to disable systemd-networkd if conflicting
- Check wireless regulatory domain: `iw reg get`

**Fedora:**
- SELinux may block operations
- Temporarily disable: `sudo setenforce 0`

---

## 📱 Testing on Different Client Devices

### Android Phones
- Should auto-detect captive portal
- Shows "Sign in to network" notification
- Portal page appears automatically

### iOS/iPhone
- Shows "captive.apple.com" check
- Portal page appears in popup
- May need to tap WiFi name after connecting

### Windows Laptops
- Shows "Action needed" notification
- Opens browser to portal page
- Works in Edge, Chrome, Firefox

### Linux Clients
- May not auto-detect captive portal
- Manually open browser
- Visit any HTTP website (not HTTPS)

---

## 🛡️ System Service Conflicts

### Disable Conflicting Services

If hostapd/dnsmasq are running as services:

```bash
# Check if services are active
systemctl status hostapd
systemctl status dnsmasq

# Stop and disable them
sudo systemctl stop hostapd dnsmasq
sudo systemctl disable hostapd dnsmasq
```

### Re-enable After Use

```bash
# If you need them as services later
sudo systemctl enable hostapd dnsmasq
sudo systemctl start hostapd dnsmasq
```

---

## 📊 Deployment Checklist

Use this checklist when deploying to a new device:

- [ ] Copy all project files to device
- [ ] Run `sudo ./setup.sh`
- [ ] Verify wireless interface detected correctly
- [ ] Customize SSID/password if needed (edit `hostapd.conf`)
- [ ] Customize portal page if needed (edit `portal.html`)
- [ ] Stop any conflicting services
- [ ] Test with `sudo ./start.sh`
- [ ] Connect a test device and verify portal appears
- [ ] Test `sudo ./stop.sh` restores WiFi
- [ ] Document device-specific notes

---

## 🔄 Creating a Portable Package

To create a deployment package for offline installation:

```bash
# Create a complete package
tar -czf captive-portal-deploy.tar.gz \
    setup.sh start.sh stop.sh \
    server.py portal.html \
    hostapd.conf dnsmasq.conf \
    README.md DEPLOY.md

# Optional: Add offline packages (Debian/Ubuntu)
apt-get download hostapd dnsmasq
mkdir offline-packages
mv *.deb offline-packages/

# Create archive with packages
tar -czf captive-portal-full.tar.gz \
    *.sh *.py *.html *.conf *.md \
    offline-packages/
```

---

## 🎓 Advanced: Auto-Start on Boot

To make the captive portal start automatically:

### Create systemd service

```bash
sudo nano /etc/systemd/system/captive-portal.service
```

Add:
```ini
[Unit]
Description=Captive Portal Hotspot
After=network.target

[Service]
Type=forking
WorkingDirectory=/path/to/portalProj
ExecStart=/path/to/portalProj/start.sh
ExecStop=/path/to/portalProj/stop.sh
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable captive-portal
sudo systemctl start captive-portal
```

---

## 📝 Summary

**Easiest deployment:**
1. Copy files to new device
2. Run `sudo ./setup.sh`
3. Run `sudo ./start.sh`

**The setup.sh script handles everything automatically!**
