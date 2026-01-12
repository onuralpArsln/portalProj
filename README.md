# WiFi Captive Portal

## Start
```bash
sudo ./start_hotspot.sh
```

## Stop
`Ctrl+C` — auto-cleans up  
Or manually: `sudo ./stop_hotspot.sh`

## WiFi Settings
Edit `hostapd.conf`:
```
ssid=CaptivePortal       # Network name
wpa_passphrase=portal123 # Password
```

## How it works
1. Device connects → captive portal popup opens automatically
2. User sees 4 buttons
3. Button clicks logged in terminal with IP & timestamp
