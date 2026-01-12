# WiFi Captive Portal

## Quick Start
```bash
sudo ./start_hotspot.sh
```

## Stop
`Ctrl+C` or `sudo ./stop_hotspot.sh`

## WiFi Settings
Edit `hostapd.conf`:
```
ssid=CaptivePortal       # Network name
wpa_passphrase=portal123 # Password
```

## What Happens
1. Phone connects to WiFi → sees 4 buttons
2. Button clicks appear in your terminal
