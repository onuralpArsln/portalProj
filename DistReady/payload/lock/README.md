# Terminal Lock System

Password protection for terminal sessions with automatic shutdown on failed attempts.

## 📁 Directory Structure

```
lock/
├── deploy_terminal_lock.sh  # Automated deployment script
├── lock.sh                   # Manual installation script
├── unlock.sh                 # Removal script
├── terminal_lock.sh          # Password verification script
└── README.md                 # This file
```

## 🚀 Quick Start

### Deployment (Recommended)
```bash
sudo ./deploy_terminal_lock.sh
```

This will automatically:
- Copy all files to `/opt/terminal_lock/`
- Install password protection
- Set up proper permissions

### Manual Installation
```bash
sudo ./lock.sh
```

### Removal
```bash
sudo /opt/terminal_lock/unlock.sh
```

## 🔐 Password

```
131619
```

## ⚙️ How It Works

1. **Installation**: Modifies shell initialization files (`.bashrc`, `.profile`)
2. **Every New Terminal**: Prompts for password
3. **3 Failed Attempts**: Device automatically shuts down
4. **Session-Based**: Same terminal doesn't ask twice

## 📦 Deployment to Multiple Devices

The deployment script ensures all devices have the lock installed to the same path:

```bash
# On each device:
cd /path/to/this/lock/directory
sudo ./deploy_terminal_lock.sh
```

All devices will have the lock at: `/opt/terminal_lock/`

## ⚠️ Important Notes

- **Test before logging out!** Open a new terminal to verify password works
- **Password must be memorized** - Recovery requires physical access
- **Do NOT delete `/opt/terminal_lock/`** after installation
- Scripts in this directory can be deleted after deployment (they're copied to `/opt/`)

## 🛠️ Files You Need After Installation

| File | Keep? | Why |
|------|-------|-----|
| `deploy_terminal_lock.sh` | Optional | Only needed for new installations |
| `lock.sh` | Optional | Copied to `/opt/terminal_lock/` |
| `unlock.sh` | Optional | Copied to `/opt/terminal_lock/` |
| `terminal_lock.sh` | Optional | Copied to `/opt/terminal_lock/` |
| `/opt/terminal_lock/terminal_lock.sh` | **REQUIRED** | System depends on this! |
| `/opt/terminal_lock/unlock.sh` | Recommended | For easy removal |

## 🔧 Changing Password

1. Edit `terminal_lock.sh`
2. Change `CORRECT_PASSWORD="131619"` to your password
3. Redeploy with `sudo ./deploy_terminal_lock.sh`

## 📝 Use Cases

- **Kiosk Deployments**: Prevent customer terminal access
- **Production Systems**: Lock down critical devices
- **Anti-Tampering**: Auto-shutdown on unauthorized access attempts
