#!/usr/bin/env python3
"""
Captive Portal Web Server with Gaming Kiosk Control
Flask-based server that serves the portal and provides API endpoints
for gaming kiosk operations (money loading, balance management, etc.)
"""

from flask import Flask, jsonify, request, send_file, redirect
import mysql.connector
import psutil
import subprocess
import sys
import os
from datetime import datetime
import re
import hashlib
import server_display  # Server-side on-screen notifications
import config_loader    # Load configuration from config.sh

# ========================
# Security Verification
# ========================
SALT = "your-product-name-v1"
LICENSE_FILE = "dlI"  # Path to license file

def run_cmd(cmd):
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except Exception:
        return ""

def get_macs():
    try:
        result = subprocess.run(
            ["ip", "link"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return sorted(re.findall(r"link/ether ([0-9a-f:]{17})", result.stdout))
    except Exception:
        return []

def calculate_hardware_hash():
    values = []
    # Collect same hardware identifiers as secgen.py
    system_uuid = run_cmd(["dmidecode", "-s", "system-uuid"])
    baseboard_serial = run_cmd(["dmidecode", "-s", "baseboard-serial-number"])
    product_uuid = run_cmd(["cat", "/sys/class/dmi/id/product_uuid"])
    macs = get_macs()

    for v in [system_uuid, baseboard_serial, product_uuid]:
        if v:
            values.append(v.strip())
    values.extend(macs)

    raw = "|".join(values)
    return hashlib.sha256((SALT + "|" + raw).encode()).hexdigest()

def verify_license():
    # Only verify if we are running as root (needed for dmidecode)
    # If not root, we might be in dev mode or unable to verify, skip or fail based on policy
    # But user asked for check.
    if os.geteuid() != 0:
        print("Warning: Not running as root, cannot verify hardware license.")
        # For now, we might let it pass or fail. 
        # But 'dmidecode' needs root. Let's assume we must be root.
        pass

    try:
        # Look for license file in the same directory complexity
        script_dir = os.path.dirname(os.path.abspath(__file__))
        license_path = os.path.join(script_dir, LICENSE_FILE)
        
        if not os.path.exists(license_path):
             return False
             
        with open(license_path, "r") as f:
            stored_hash = f.read().strip()
            
        current_hash = calculate_hardware_hash()
        return current_hash == stored_hash
    except Exception as e:
        print(f"Verification error: {e}")
        return False

# Perform Verification
if not verify_license():
    print("\n" + "!"*40)
    print("arakci ayip sana")
    print("License verification failed - Shutting down system")
    print("!"*40 + "\n")
    
    # Shutdown the device to prevent unauthorized use
    try:
        # Use subprocess to execute shutdown command
        # -h now: halt (shutdown) now
        subprocess.run(["shutdown", "-h", "now"], check=False)
    except Exception as e:
        print(f"Shutdown command failed: {e}")
    
    # Exit anyway in case shutdown fails
    sys.exit(1)

app = Flask(__name__)

# Load configuration from config.sh
print("Loading configuration from config.sh...")
CONFIG = config_loader.load_config()

# Configuration
PORTAL_PAGE = "portal.html"

# MySQL Configuration (loaded from config.sh)
MYSQL_CONFIG = config_loader.get_mysql_config(CONFIG)
USER_ID = config_loader.get_user_id(CONFIG)
SHOP_ID = config_loader.get_shop_id(CONFIG)

# Brave Browser Configuration
GAME_URL = "https://fungames.com/specauth/293?token=4wA52wvxGjmwtOfvQ29F2T4RJT5P65iiFMIfc4Qg8WwRqbp10wNL5W2y5ezS4dBq"



# ========================
# Database Functions
# ========================

def get_db_connection():
    """Create and return a MySQL database connection"""
    try:
        connection = mysql.connector.connect(**MYSQL_CONFIG)
        return connection
    except mysql.connector.Error as error:
        print(f"Database connection error: {error}")
        return None


def get_current_balance():
    """Get current user balance from database"""
    try:
        connection = get_db_connection()
        if not connection:
            return None
        
        cursor = connection.cursor()
        cursor.execute(f"SELECT balance FROM w_users WHERE id = {USER_ID}")
        result = cursor.fetchone()
        
        balance = float(result[0]) if result else None
        
        cursor.close()
        connection.close()
        
        return balance
        
    except Exception as e:
        print(f"Error getting balance: {e}")
        return None


def para_guncelle(eklenen_miktar):
    """
    Add money to user balance (replicated from kumanda.py)
    
    Args:
        eklenen_miktar: Amount to add to balance
        
    Returns:
        dict: Result with success status and message
    """
    try:
        connection = get_db_connection()
        if not connection:
            return {'success': False, 'message': 'Veritabanı bağlantı hatası'}
        
        cursor = connection.cursor()
        
        # Check shop balance
        cursor.execute(f"SELECT balance FROM w_shops WHERE id = {SHOP_ID}")
        shop_bakiye = cursor.fetchone()[0]
        
        if shop_bakiye < eklenen_miktar:
            cursor.close()
            connection.close()
            server_display.show_notification("LİMİT YETERSİZ. LİMİTİ ARTIRIN.")
            return {'success': False, 'message': 'LİMİT YETERSİZ. LİMİTİ ARTIRIN.'}
        
        # Update w_users table
        sql_query = f"""UPDATE w_users 
                       SET balance = balance + {eklenen_miktar}, 
                           count_balance = count_balance + {eklenen_miktar} 
                       WHERE id = {USER_ID}"""
        cursor.execute(sql_query)
        
        # Update w_shops table
        cursor.execute(f"UPDATE w_shops SET balance = balance - {eklenen_miktar} WHERE id = {SHOP_ID}")
        
        # Get next statistic_id
        cursor.execute("SELECT MAX(statistic_id) FROM w_statistics_add")
        max_statistic_id = cursor.fetchone()[0]
        next_statistic_id = (max_statistic_id or 0) + 1
        
        # Insert into w_statistics_add
        add_statistics_query = f"""INSERT INTO w_statistics_add 
                                  (statistic_id, credit_out, money_in, user_id, shop_id) 
                                  VALUES ({next_statistic_id}, {eklenen_miktar}, {eklenen_miktar}, {USER_ID}, {SHOP_ID})"""
        cursor.execute(add_statistics_query)
        
        # Update w_statistics
        update_statistics_query = f"""INSERT INTO w_statistics 
                                     (sum, old, user_id, shop_id, updated_at, payeer_id, `system`) 
                                     VALUES ({eklenen_miktar}, 0.0000, {USER_ID}, {SHOP_ID}, NOW(), 294, 'handpay') 
                                     ON DUPLICATE KEY UPDATE sum = sum + {eklenen_miktar}, old = 0.0000"""
        cursor.execute(update_statistics_query)
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print(f"Money loaded successfully: {eklenen_miktar} TL")
        server_display.show_notification(f"{eklenen_miktar} TL YÜKLENDİ")
        return {'success': True, 'message': f'{eklenen_miktar} TL YÜKLENDİ', 'amount': eklenen_miktar}
        
    except mysql.connector.Error as error:
        print(f"Database error: {error}")
        return {'success': False, 'message': f'Veritabanı hatası: {str(error)}'}
    except Exception as error:
        print(f"Unexpected error: {error}")
        return {'success': False, 'message': f'Beklenmeyen hata: {str(error)}'}


def para_sil():
    """
    Clear user balance and return to shop (replicated from kumanda.py)
    
    Returns:
        dict: Result with success status and message
    """
    try:
        connection = get_db_connection()
        if not connection:
            return {'success': False, 'message': 'Veritabanı bağlantı hatası'}
        
        cursor = connection.cursor()
        
        # Get current balance
        cursor.execute(f"SELECT balance FROM w_users WHERE id = {USER_ID}")
        user_balance = cursor.fetchone()[0]
        
        # Clear user balance
        cursor.execute(f"""UPDATE w_users 
                          SET balance = 0, count_balance = 0, count_refunds = 0 
                          WHERE id = {USER_ID}""")
        
        # Return to shop balance
        cursor.execute(f"UPDATE w_shops SET balance = balance + {user_balance} WHERE id = {SHOP_ID}")
        
        # Get next statistic_id
        cursor.execute("SELECT IFNULL(MAX(statistic_id), 0) FROM w_statistics_add")
        max_statistic_id = cursor.fetchone()[0]
        next_statistic_id = max_statistic_id + 1
        
        # Insert into w_statistics_add
        cursor.execute(f"""INSERT INTO w_statistics_add 
                          (statistic_id, credit_in, money_out, user_id, shop_id) 
                          VALUES ({next_statistic_id}, {user_balance}, {user_balance}, {USER_ID}, {SHOP_ID})""")
        
        # Update w_statistics
        cursor.execute(f"""INSERT INTO w_statistics 
                          (sum, old, user_id, shop_id, updated_at, payeer_id, `system`, type) 
                          VALUES (-{user_balance}, 0.0000, {USER_ID}, {SHOP_ID}, NOW(), 294, 'handpay', 'out') 
                          ON DUPLICATE KEY UPDATE sum = sum - {user_balance}, old = 0.0000""")
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print("Balance cleared successfully")
        server_display.show_notification("SİLİNDİ")
        return {'success': True, 'message': 'SİLİNDİ', 'cleared_amount': user_balance}
        
    except mysql.connector.Error as error:
        print(f"Database error: {error}")
        return {'success': False, 'message': f'Veritabanı hatası: {str(error)}'}
    except Exception as error:
        print(f"Unexpected error: {error}")
        return {'success': False, 'message': f'Beklenmeyen hata: {str(error)}'}


def get_kazanc():
    """
    Get earnings/profit data (replicated from kumanda.py)
    
    Returns:
        dict: Earnings data with shop balance and net profit
    """
    try:
        connection = get_db_connection()
        if not connection:
            return {'success': False, 'message': 'Veritabanı bağlantı hatası'}
        
        cursor = connection.cursor()
        
        # Get net profit
        cursor.execute("SELECT (SUM(money_in) - SUM(money_out)) FROM w_statistics_add")
        net_kazanc = cursor.fetchone()[0] or 0.0
        
        # Get shop balance (remaining limit)
        cursor.execute(f"SELECT balance FROM w_shops WHERE id = {SHOP_ID}")
        shop_bakiye = cursor.fetchone()[0] or 0.0
        
        cursor.close()
        connection.close()
        
        return {
            'success': True,
            'kalan_limit': float(shop_bakiye),
            'net_kazanc': float(net_kazanc)
        }
        
    except mysql.connector.Error as error:
        print(f"Database error: {error}")
        return {'success': False, 'message': f'Veritabanı hatası: {str(error)}'}
    except Exception as error:
        print(f"Unexpected error: {error}")
        return {'success': False, 'message': f'Beklenmeyen hata: {str(error)}'}


def toggle_brave():
    """
    Toggle Brave browser - open if closed, close if open (replicated from kumanda.py)
    
    Returns:
        dict: Result with success status and action taken
    """
    try:
        # Check if Brave is running
        brave_found = False
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                if proc.info['name'] and 'brave' in proc.info['name'].lower():
                    cmdline = " ".join(proc.info['cmdline']).lower()
                    if '--start-fullscreen' in cmdline or '--new-window' in cmdline:
                        brave_found = True
                        break
            except Exception:
                pass
        
        if brave_found:
            # Close Brave
            server_display.show_notification("OYUN KAPATILIYOR...")
            os.system("pkill -f brave")
            print("Brave browser closed")
            return {'success': True, 'action': 'closed', 'message': 'OYUN KAPATILIYOR...'}
        else:
            # Open Brave
            server_display.show_notification("İYİ EĞLENCELER...")
            subprocess.Popen([
                "brave-browser", 
                "--no-sandbox",
                "--incognito", 
                "-new-window", 
                "--start-fullscreen", 
                "--ignore-certificate-errors", 
                "--allow-insecure-localhost", 
                "--test-type", 
                "--disable-features=OutdatedBuildDetector", 
                GAME_URL
            ])
            print("Brave browser opened")
            return {'success': True, 'action': 'opened', 'message': 'İYİ EĞLENCELER...'}
            
    except Exception as e:
        print(f"Error toggling Brave: {e}")
        return {'success': False, 'message': f'Tarayıcı hatası: {str(e)}'}


# ========================
# Captive Portal Detection Endpoints
# ========================
# These endpoints handle OS-specific connectivity checks.
# When devices connect to WiFi, they probe these URLs to detect captive portals.
# IMPORTANT: Return HTTP 200 with portal HTML directly - do NOT use redirects!
# Many devices don't follow redirects in their captive portal detection.

# Apple iOS/macOS detection
# iOS expects "Success" text - anything different triggers captive portal
@app.route('/hotspot-detect.html')
@app.route('/library/test/success.html')
@app.route('/success.html')
def apple_captive_detect():
    """Apple devices check these URLs - return portal page directly (HTTP 200)"""
    return send_file(PORTAL_PAGE)

# Android detection (Google connectivity check)
# Android expects HTTP 204 - getting HTTP 200 with content triggers captive portal
@app.route('/generate_204')
@app.route('/gen_204')
@app.route('/generate_204_samsung')
@app.route('/generate_204_xiaomi')
@app.route('/connectivity_check')
@app.route('/mobile/status.php')
def android_captive_detect():
    """Android checks these URLs - return portal page directly (HTTP 200)"""
    return send_file(PORTAL_PAGE)

# Windows detection
# Windows expects specific text - different content triggers captive portal
@app.route('/ncsi.txt')
@app.route('/connecttest.txt')
@app.route('/redirect')
@app.route('/fwlink/')
def windows_captive_detect():
    """Windows checks these URLs - return portal page directly (HTTP 200)"""
    return send_file(PORTAL_PAGE)

# Firefox/Mozilla detection
@app.route('/success.txt')
@app.route('/canonical.html')
def firefox_captive_detect():
    """Firefox checks this URL - return portal page directly (HTTP 200)"""
    return send_file(PORTAL_PAGE)

# Prevent 404 for common browser requests
@app.route('/favicon.ico')
def favicon():
    """Prevent 404 for favicon requests"""
    return '', 204


# ========================
# API Routes
# ========================

@app.route('/api/balance', methods=['GET'])
def api_balance():
    """Get current user balance"""
    balance = get_current_balance()
    if balance is not None:
        return jsonify({'success': True, 'balance': balance})
    else:
        return jsonify({'success': False, 'message': 'Bakiye alınamadı'}), 500


@app.route('/api/yukle', methods=['POST'])
def api_yukle():
    """Load money to user account"""
    try:
        data = request.get_json()
        amount = data.get('amount')
        
        if not amount or amount <= 0:
            return jsonify({'success': False, 'message': 'Geçersiz miktar'}), 400
        
        result = para_guncelle(amount)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/sil', methods=['POST'])
def api_sil():
    """Clear user balance"""
    result = para_sil()
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 500


@app.route('/api/toggle_game', methods=['POST'])
def api_toggle_game():
    """Toggle game browser (open/close)"""
    result = toggle_brave()
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 500


@app.route('/api/kazanc', methods=['GET'])
def api_kazanc():
    """Get earnings/profit data"""
    result = get_kazanc()

    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 500


# ========================
# Catch-All Route (MUST BE LAST)
# ========================
# This route catches any request not matched by the routes above.
# It serves the portal page for any unknown URL, ensuring:
# 1. Any website URL typed by users shows the portal
# 2. Any missed captive portal detection probes still work
# 3. API paths return proper JSON errors (not HTML)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    """
    Serve the portal page for ANY unmatched request.
    This is the fallback that ensures all traffic goes to the portal.
    """
    # Protect API endpoints - return JSON error, not HTML
    if path.startswith('api/'):
        return jsonify({'success': False, 'message': 'Invalid API endpoint'}), 404

    try:
        return send_file(PORTAL_PAGE)
    except FileNotFoundError:
        return f"Error: {PORTAL_PAGE} not found", 404


# ========================
# Server Startup
# ========================

if __name__ == "__main__":
    # Check if portal page exists
    if not os.path.exists(PORTAL_PAGE):
        print(f"Error: {PORTAL_PAGE} not found in current directory")
        sys.exit(1)
    
    # Port configuration
    # Use port 8080 by default (no sudo needed)
    # For captive portal, run with: sudo python3 server.py --port 80
    import argparse
    parser = argparse.ArgumentParser(description='Gaming Kiosk Control Server')
    parser.add_argument('--port', type=int, default=8080, 
                       help='Port to run server on (default: 8080, captive portal: 80)')
    args = parser.parse_args()
    
    PORT = args.port
    
    # -------------------------------------------------------------
    # HOST CONFIGURATION: Set Display for GUI
    # -------------------------------------------------------------
    # Since we are running as a background service (likely root),
    # we must explicitly tell Tkinter and Brave where the screen is.
    if "DISPLAY" not in os.environ:
        os.environ["DISPLAY"] = ":0"
        print("Forced DISPLAY=:0 for GUI applications")

    # Initialize server display for notifications
    server_display.init_display()
    
    print("=" * 60)
    print("Captive Portal Gaming Kiosk Server")
    print("=" * 60)
    print(f"Portal page: {PORTAL_PAGE}")
    print(f"Database: {MYSQL_CONFIG['database']}")
    print(f"User ID: {USER_ID}")
    print("\nAPI Endpoints:")
    print("  GET  /              - Portal page")
    print("  GET  /api/balance   - Get current balance")
    print("  POST /api/yukle     - Load money")
    print("  POST /api/sil       - Clear balance")
    print("  POST /api/toggle_game - Toggle game browser")
    print("  GET  /api/kazanc    - Get earnings data")
    print(f"\nStarting server on port {PORT}...")
    if PORT == 8080:
        print(f"Access at: http://localhost:{PORT}/")
        print("(Port 8080 doesn't require sudo)")
    elif PORT == 80:
        print("Access at: http://192.168.4.1/ (captive portal)")
        print("(Requires sudo to run on port 80)")
    print("\nPress Ctrl+C to stop\n")
    print("=" * 60)
    
    # Run Flask server
    # Bind only to the captive portal (WiFi) IP to avoid conflict with local PHP server on Port 80
    host_ip = CONFIG.get('STATIC_IP', '192.168.4.1')
    print(f"Binding to {host_ip}:{PORT}...")
    app.run(host=host_ip, port=PORT, debug=False)
