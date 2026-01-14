# Gaming Kiosk Captive Portal

Web-based control panel for gaming kiosk operations with captive portal WiFi.

## Quick Start

### 1. Find Your WiFi Interface
```bash
./find_interface.sh
```

### 2. Configure Interface
Edit `config.sh` and set your WiFi interface:
```bash
INTERFACE="wlan0"  # Change to your interface name
```

### 3. Install Dependencies
```bash
sudo ./install_deps.sh
```

### 4. Start Captive Portal
```bash
sudo ./start.sh
```

### 5. Stop Captive Portal
```bash
sudo ../stop.sh
```

## Configuration

All settings are in `config.sh`:
- **INTERFACE**: WiFi interface name (wlan0, wlan1, etc.)
- **STATIC_IP**: Gateway IP (default: 192.168.4.1)
- **SSID**: WiFi network name
- **WPA_PASSPHRASE**: WiFi password
- **Database settings**: MySQL credentials

## Features

- 💰 Load money (1 TL, 100 TL, 500 TL, custom amounts)
- 🗑️ Clear balance
- 🎮 Toggle game browser
- 📊 Show earnings
- 🔄 Auto-redirect to portal when devices connect

## Access

- **Testing**: http://localhost:8080 (run: `python3 server.py`)
- **Captive Portal**: http://192.168.4.1 (auto-redirects when connected to WiFi)

## Files

- `config.sh` - Main configuration (edit this!)
- `start.sh` - Start captive portal
- `server.py` - Flask web server
- `portal.html` - Gaming kiosk interface
- `install_deps.sh` - Install dependencies
- `find_interface.sh` - Detect WiFi interfaces

## Troubleshooting

**Can't find WiFi interface?**
```bash
./find_interface.sh
```

**Server won't start?**
```bash
# Check logs
cat /tmp/portal-server.log

# Verify dependencies
sudo ./install_deps.sh
```

**Wrong interface?**
Edit `config.sh` and change `INTERFACE="wlan0"` to your interface name.
