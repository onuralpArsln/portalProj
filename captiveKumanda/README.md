# Gaming Kiosk Captive Portal

Web-based gaming kiosk control panel with WiFi captive portal. Centralized configuration with automatic WiFi detection.

## 🚀 Quick Start (New Device)

```bash
cd ~/captiveKumanda
sudo ./install.sh           # Install all dependencies + auto-detect WiFi
nano config.sh              # (Optional) Customize SSID, password, database
sudo ./start.sh             # Start portal
```

Connect to WiFi "CaptivePortal" (password: portal123) → Portal opens at http://192.168.4.1

## 🛑 Stop Portal

```bash
sudo ./stop.sh
```

## ⚙️ Configuration (config.sh)

All settings in one file - all scripts read from here:

```bash
INTERFACE="wlan0"           # Auto-detected by install.sh
SSID="CaptivePortal" 
WPA_PASSPHRASE="portal123"
STATIC_IP="192.168.4.1"
SERVER_PORT="80"
MYSQL_USER="fungames"
MYSQL_PASSWORD="7396Ksn!"
MYSQL_DATABASE="fungames"
USER_ID="320"
SHOP_ID="1"
```

After editing config.sh: `sudo ./configure.sh` to sync all files.

## 📁 Files

| File | Purpose |
|------|---------|
| `config.sh` | Central configuration |
| `install.sh` | Install dependencies + auto-configure |
| `configure.sh` | Auto-detect WiFi & sync configs |
| `start.sh` | Start portal |
| `stop.sh` | Stop portal |
| `server.py` | Flask web server |
| `config_loader.py` | Python config reader |
| `portal.html` | Web interface |

## 🎮 Features

💰 Load money • 🗑️ Clear balance • 🎮 Toggle game • 📊 View earnings • 🔄 Auto-redirect to portal

## 🔧 Commands

```bash
# Test config
python3 config_loader.py

# View logs
tail -f /tmp/portal-server.log
tail -f /tmp/hostapd.log

# Check interface
ip link show
cat config.sh | grep INTERFACE
```

## 🛠️ Troubleshooting

**No WiFi interface found:**
```bash
ip link show                # List interfaces
nano config.sh              # Edit INTERFACE manually
sudo ./configure.sh         # Sync configs
```

**hostapd fails:**
```bash
iw list | grep "interface modes" -A 8  # Check AP mode support
nano config.sh              # Try CHANNEL="1" or "11"
sudo ./configure.sh && sudo ./start.sh
```

**Port 80 in use:**
```bash
sudo lsof -i :80            # Check what uses port 80
sudo systemctl stop apache2 # Stop conflicting service
# OR: Edit SERVER_PORT in config.sh
```

**Database error:**
```bash
nano config.sh              # Verify MYSQL_* settings
sudo systemctl status mysql # Check MySQL running
python3 config_loader.py    # Test config loading
```

**NetworkManager conflict:**
```bash
sudo ./stop.sh && sudo ./start.sh  # Clean restart
```

## 📦 Auto-Start on Boot

```bash
sudo nano /etc/systemd/system/captive-portal.service
```

```ini
[Unit]
Description=Captive Portal
After=network.target

[Service]
Type=forking
User=root
WorkingDirectory=/path/to/captiveKumanda
ExecStart=/path/to/captiveKumanda/start.sh
ExecStop=/path/to/captiveKumanda/stop.sh

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable captive-portal
```

## 🔐 Security

```bash
chmod 600 config.sh                 # Protect credentials
echo "config.sh" >> .gitignore      # Don't commit passwords
```

## 📊 Requirements

- Linux (Ubuntu/Debian/Raspberry Pi OS)
- WiFi adapter with AP mode support
- Root/sudo access
- Python 3.x

## 🔄 Workflow

**Daily Use:** `sudo ./start.sh` → `sudo ./stop.sh`  
**Config Change:** Edit `config.sh` → `sudo ./configure.sh` → `sudo ./start.sh`  
**New Device:** `sudo ./install.sh` → `sudo ./start.sh`
