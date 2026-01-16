# Captive Portal - Deployment Package

## 📦 Package Contents

```
payload/
├── captive_portal           # Main executable (bundled, 19MB)
├── setup/                   # Installation & configuration scripts
├── lock/                    # Terminal password lock system
├── security/                # License generation tools
└── captive_portal.service   # Systemd service file (optional)
```

---

## 🚀 Quick Deployment (3 Steps)

### Step 1: Install Dependencies & Generate Configs
```bash
cd payload
sudo ./setup/install_offline.sh
```

**This automatically:**
- ✅ Installs system packages (hostapd, dnsmasq, etc.)
- ✅ Installs Python packages (Flask, MySQL, etc.)
- ✅ Generates `config.sh`, `hostapd.conf`, `dnsmasq.conf`
- ✅ Detects WiFi interface automatically
- ✅ Generates hardware license (`dlI` file)
- ✅ Locks configuration files

### Step 2: Install Terminal Lock (Optional)
```bash
cd lock
sudo ./deploy_terminal_lock.sh
cd ..
```

**Password:** `131619`

### Step 3: Deploy to Production
```bash
sudo mkdir -p /opt/captive_portal
sudo cp captive_portal /opt/captive_portal/
sudo cp config.sh /opt/captive_portal/
sudo cp hostapd.conf /opt/captive_portal/
sudo cp dnsmasq.conf /opt/captive_portal/
sudo cp security/dlI /opt/captive_portal/
```

### Step 4: Cleanup (Optional)
```bash
# Delete temporary deployment folders
rm -rf setup/ lock/ security/
```

---

## ▶️ Running the Captive Portal

### Manual Start
```bash
cd /opt/captive_portal
sudo ./captive_portal
```

Press `Ctrl+C` to stop.

### Auto-Start on Boot (Optional)
```bash
sudo cp captive_portal.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable captive_portal
sudo systemctl start captive_portal
```

Check status:
```bash
sudo systemctl status captive_portal
```

---

## 📁 Final Production Structure

After deployment, `/opt/captive_portal/` contains:

```
/opt/captive_portal/
├── captive_portal       # Executable (contains all dependencies)
├── config.sh            # Network/database configuration
├── hostapd.conf         # WiFi access point settings
├── dnsmasq.conf         # DNS/DHCP server settings
└── dlI                  # Hardware license file
```

**⚠️ IMPORTANT:**
- The executable needs ALL 4 config files in the same directory
- Do NOT delete `dlI` - license verification will fail
- Do NOT delete `/opt/captive_portal/` while the portal is running

---

## ⚙️ Configuration

### Edit Network Settings
```bash
# Unlock config files first
sudo chattr -i /opt/captive_portal/config.sh
sudo nano /opt/captive_portal/config.sh

# Important variables:
# INTERFACE="wlan0"           # WiFi adapter
# SSID="CaptivePortal"         # WiFi network name
# WPA_PASSPHRASE="portal123"   # WiFi password
# STATIC_IP="192.168.4.1"      # Gateway IP

# Lock again
sudo chattr +i /opt/captive_portal/config.sh
```

### Edit Database Settings
```bash
# In config.sh:
# MYSQL_USER="fungames"
# MYSQL_PASSWORD="password"
# MYSQL_DATABASE="fungames"
# USER_ID="320"
# SHOP_ID="1"
```

---

## 🔧 Troubleshooting

### Check Logs
```bash
# Hostapd log
tail -f /tmp/hostapd.log

# Dnsmasq log
tail -f /tmp/dnsmasq.log

# Web server log
tail -f /tmp/portal-server.log

# Systemd log (if using service)
journalctl -u captive_portal -f
```

### Common Issues

**WiFi not appearing:**
- Check interface name in `config.sh`
- Run `ip link show` to see available interfaces
- Verify WiFi adapter supports AP mode

**Clients can't connect:**
- Check hostapd is running: `pgrep hostapd`
- Check channel conflicts: Try changing `CHANNEL` in `config.sh`

**Portal not loading:**
- Check web server is running: `pgrep -f captive_portal`
- Check port 80 is not in use: `sudo lsof -i :80`
- Check iptables rules: `sudo iptables -L -n -v`

**License error:**
- Regenerate license: `cd security && sudo python3 secgen.py`
- Copy new `dlI` to `/opt/captive_portal/`

---

## 🔐 Security Features

### Hardware License Lock
- The executable verifies hardware fingerprint at startup
- If license doesn't match, system shuts down automatically
- Each device needs its own unique `dlI` file

### Terminal Password Lock
- Protects all terminal access with password `131619`
- 3 failed attempts = automatic system shutdown
- To remove: `sudo /opt/terminal_lock/unlock.sh`

---

## 📊 System Requirements

- **OS:** Linux (Ubuntu, Debian, etc.)
- **Privileges:** Root access (sudo)
- **WiFi:** Adapter that supports AP mode
- **Ports:** 80 (HTTP), 53 (DNS)
- **Disk:** ~50MB for executable + configs

---

## 📝 Notes

- Executable size: **19MB** (contains Python + all dependencies)
- No Python installation required on target device
- Self-contained: Works on any Linux system
- Offline deployment: No internet needed after initial package transfer

---

## 🆘 Support

For issues or questions, review the implementation plan:
`bundled_executable_plan.md`
