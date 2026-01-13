# Captive Portal Hotspot

Transform your Linux device into a WiFi hotspot with captive portal using hostapd and dnsmasq.

## Quick Start

### First Time Setup (New Device)
```bash
sudo ./setup.sh
```
This will auto-detect your wireless interface, install dependencies, and configure everything automatically.

### Start the Hotspot
```bash
sudo ./start.sh
```

### Stop the Hotspot
```bash
sudo ./stop.sh
```

## Connection Details

- **SSID**: CaptivePortal
- **Password**: portal123
- **Gateway**: 192.168.4.1
- **DHCP Range**: 192.168.4.2 - 192.168.4.20

## Files

- `setup.sh` - **NEW!** Auto-setup script for new devices
- `start.sh` - Start the captive portal hotspot
- `stop.sh` - Stop and restore normal WiFi
- `server.py` - Python web server for portal page
- `portal.html` - Captive portal landing page
- `hostapd.conf` - WiFi access point configuration
- `dnsmasq.conf` - DHCP and DNS configuration

## Deployment

For deploying on different devices, see **[DEPLOY.md](DEPLOY.md)** for a complete tutorial.

## How It Works

1. **start.sh** stops NetworkManager on wlan0, configures static IP, starts hostapd (WiFi AP), dnsmasq (DHCP/DNS), sets up iptables redirect, and launches the web server
2. Connected devices receive captive portal page automatically
3. **stop.sh** cleanly shuts down all services and restores WiFi to NetworkManager

## Requirements

- Linux with NetworkManager
- hostapd installed
- dnsmasq installed
- Python 3
- Root/sudo access

## Logs

- `/tmp/hostapd.log` - WiFi access point logs
- `/tmp/dnsmasq.log` - DHCP/DNS logs
- `/tmp/portal-server.log` - Web server request logs

## Testing

After starting, connect another device to "CaptivePortal" WiFi. The portal page should appear automatically.

## Troubleshooting

If the hotspot won't start, check that:
- wlan0 is available: `ip link show`
- No other hostapd/dnsmasq instances running
- You have root privileges

To manually restore WiFi:
```bash
sudo nmcli device set wlan0 managed yes
sudo systemctl restart NetworkManager
```

---

**Note**: This setup does not provide internet access by default. It's designed for captive portal demonstration. To add internet sharing, enable IP forwarding and NAT.
