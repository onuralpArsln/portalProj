#!/usr/bin/env python3
"""
kumanda_test.py - Mock Arduino ile test için kumanda.py'nin değiştirilmiş versiyonu

Bu dosya, kumanda.py'nin sanal seri port ile çalışacak şekilde değiştirilmiş halidir.
mock_arduino_socat.py ile birlikte kullanılır.

KULLANIM:
1. Terminal 1'de: python3 mock_arduino_socat.py
2. Terminal 2'de: python3 kumanda_test.py
"""

import tkinter as tk
from tkinter import ttk
import serial
import serial.tools.list_ports
import threading
import time
import psutil
import subprocess
import sys
import mysql.connector
from mysql.connector.locales.eng import client_error
import os
from cryptography.fernet import Fernet, InvalidToken

# --- TEST MODU: Sanal port kullan ---
TEST_MODE = True
VIRTUAL_PORT = "/tmp/ttyVirtual1"  # mock_arduino_socat.py'nin oluşturduğu port

# --- Yapılandırma ---
ARDUINO_VID = ["1A86", "2341"]
ARDUINO_PID = ["7523", "8037"]

BRAVE_PATH = {
    "Windows": r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    "Darwin": "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "Linux": "/usr/bin/brave-browser"
}

KEY_B64 = b"o3QqhjSBDaIEhd8h_e8icgou0socOWYTG9S_eFIALo0="
F = Fernet(KEY_B64)

# --- Global Değişkenler ---
ser = None
data_queue = []
app_running = True
notification_window = None
auth = False
kurulum = False
id = None
kazanc_window = None
last_known_balance = None

def decrypt_text(b: bytes) -> str:
    return F.decrypt(b).decode("utf-8")

try:
    with open("open_id.txt", "r") as f:
        content = f.read()
        id = decrypt_text(content)
        kurulum = True
except FileNotFoundError:
    print("kurulum yapılmamış.")


def find_arduino_port(vid_list, pid_list):
    """TEST MODU: Sanal portu döndürür."""
    if TEST_MODE:
        if os.path.exists(VIRTUAL_PORT):
            print(f"[TEST] Sanal port kullanılıyor: {VIRTUAL_PORT}")
            return VIRTUAL_PORT
        else:
            print(f"[TEST] Sanal port bulunamadı: {VIRTUAL_PORT}")
            print("[TEST] Önce mock_arduino_socat.py'yi çalıştırın!")
            return None
    
    # Normal mod - orijinal kod
    ports = serial.tools.list_ports.comports()
    if not isinstance(vid_list, (list, tuple)):
        vid_list = [vid_list]
    if not isinstance(pid_list, (list, tuple)):
        pid_list = [pid_list]

    for p in ports:
        try:
            if p.vid is not None and p.pid is not None:
                vid_hex = f"{p.vid:04X}"
                pid_hex = f"{p.pid:04X}"
                if vid_hex.upper() in [v.upper() for v in vid_list] and pid_hex.upper() in [p.upper() for p in pid_list]:
                    return p.device
        except (ValueError, TypeError):
            continue
    return None


def send_to_arduino(command_str):
    """Arduino'ya seri port üzerinden komut gönderir."""
    global ser
    if is_serial_alive(ser):
        try:
            ser.write(f"{command_str}\n".encode('utf-8'))
            print(f"Arduino'ya gönderildi: {command_str}")
        except Exception as e:
            print(f"Arduino'ya yazma hatası: {e}")
    else:
        print("Arduino'ya gönderilemedi: Bağlantı yok.")


def read_serial_data():
    """Seri porttan verileri ayrı bir thread'de okur."""
    global ser, data_queue, app_running
    while app_running:
        if is_serial_alive(ser):
            try:
                if ser.in_waiting > 0:
                    data = ser.readline().decode('utf-8').strip()
                    data_queue.append(data)
                    print(f"Alındı: {data}")
            except serial.SerialException as e:
                print(f"Seri port hatası: {e}")
                ser = None
            except Exception as e:
                print(f"Seri okuma thread'inde beklenmeyen hata: {e}")
        time.sleep(0.1)


def get_current_balance():
    """Veritabanından mevcut kullanıcı bakiyesini çeker."""
    try:
        mysql_user = 'fungames'
        mysql_password = '7396Ksn!'
        database = 'fungames'
        userId = 320
        
        connection = mysql.connector.connect(
            user=mysql_user,
            password=mysql_password,
            database=database,
            ssl_disabled=True,
            connection_timeout=5
        )
        cursor = connection.cursor()
        cursor.execute(f"SELECT balance FROM w_users WHERE id = {userId}")
        result = cursor.fetchone()
        
        if result:
            return float(result[0])
        else:
            return None
            
    except Exception as e:
        print(f"Bakiye okuma hatası: {e}")
        return None
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()


def sil_function():
    """'Sil' komutu alındığında çalıştırılacak fonksiyon."""
    print("Sil fonksiyonu çalıştırıldı.")
    para_sil()
    show_notification("SİLİNDİ")


def yukle_function(value):
    """'Yükle x' komutu alındığında çalıştırılacak fonksiyon."""
    print(f"Yükle fonksiyonu çalıştırıldı, değer: {value}")
    success = para_guncelle(value)
    if success:
        show_notification(f"{value} TL YÜKLENDİ")


def check_balance_for_game():
    """Bakiyeyi periyodik olarak kontrol eder."""
    global last_known_balance
    
    current_balance = get_current_balance()
    
    if current_balance is None:
        print("Bakiye kontrolü başarısız (DB hatası?), 3 saniye sonra tekrar denenecek.")
        root.after(3000, check_balance_for_game)
        return

    if last_known_balance is None:
        last_known_balance = current_balance
        print(f"Başlangıç bakiyesi ayarlandı: {last_known_balance}")
    
    elif current_balance < last_known_balance:
        if current_balance == 0:
            print(f"Bakiye sıfırlandı (para_sil). Arduino'ya sinyal GÖNDERİLMEDİ.")
        else:
            print(f"HARCAMA TESPİT EDİLDİ! Eski: {last_known_balance}, Yeni: {current_balance}")
            show_notification_top("Sakızınız Afiyet Olsun! İyi Eğlenceler...")
            send_to_arduino("111111")
        
        last_known_balance = current_balance
        
    elif current_balance > last_known_balance:
        print(f"Bakiye artışı tespit edildi (para_guncelle).")
        last_known_balance = current_balance
    
    root.after(1000, check_balance_for_game)


def toggle_brave():
    """Brave tarayıcısını açar veya kapatır."""
    brave_process_found = False
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            if proc.info['name'] and 'brave' in proc.info['name'].lower():
                cmdline = " ".join(proc.info['cmdline']).lower()
                if '--start-fullscreen' in cmdline or '--new-window' in cmdline:
                    brave_process_found = True
        except Exception as e:
            print(e)
    if brave_process_found:
        show_notification("OYUN KAPATILIYOR...")        
        os.system("pkill -f brave")
    else:
        print("Brave kapalı, açılıyor...")
        show_notification("İYİ EĞLENCELER...")
        platform = sys.platform
        url = "https://fungames.com/specauth/293?token=4wA52wvxGjmwtOfvQ29F2T4RJT5P65iiFMIfc4Qg8WwRqbp10wNL5W2y5ezS4dBq"
        proc = subprocess.Popen(["brave-browser", "--incognito","-new-window","--start-fullscreen", "--ignore-certificate-errors", "--allow-insecure-localhost" , "--test-type", "--disable-features=OutdatedBuildDetector" , url])


def show_notification(message):
    """Ekran çözünürlüğüne duyarlı bildirim penceresi gösterir."""
    global notification_window
    
    if not root:
        print("Hata: Tkinter ana penceresi (root) başlatılmamış.", file=sys.stderr)
        return

    if notification_window and notification_window.winfo_exists():
        notification_window.destroy()

    notification_window = tk.Toplevel(root)
    notification_window.overrideredirect(True)
    notification_window.attributes("-topmost", True)

    MAIN_BG_COLOR = "#2C3E50"
    BORDER_COLOR = "#FFD700"
    TEXT_COLOR = "#ECF0F1"
    
    FRAME_BORDER_THICKNESS = 6
    LABEL_PADX = 50
    LABEL_PADY = 40

    root.update_idletasks() 
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    notification_width = int(screen_width * 0.80)
    notification_height = int(screen_height * 0.25)
    
    x_pos = (screen_width // 2) - (notification_width // 2)
    y_pos = (screen_height // 2) - (notification_height // 2)

    notification_window.geometry(f"{notification_width}x{notification_height}+{x_pos}+{y_pos}")

    total_horizontal_padding = (FRAME_BORDER_THICKNESS * 2) + (LABEL_PADX * 2)
    total_vertical_padding = (FRAME_BORDER_THICKNESS * 2) + (LABEL_PADY * 2)

    available_width = notification_width - total_horizontal_padding
    available_height = notification_height - total_vertical_padding
    
    font_size_in_pixels = int(available_height * 0.8)
    font_size_in_pixels = max(10, font_size_in_pixels)
    dynamic_font_size = -font_size_in_pixels

    wrap_length_pixels = max(1, available_width)

    main_frame = tk.Frame(notification_window, bg=BORDER_COLOR, padx=FRAME_BORDER_THICKNESS, pady=FRAME_BORDER_THICKNESS) 
    main_frame.pack(expand=True, fill="both")
    
    content_frame = tk.Frame(main_frame, bg=MAIN_BG_COLOR)
    content_frame.pack(expand=True, fill="both")

    label = tk.Label(
        content_frame, 
        text=message, 
        font=("Arial", dynamic_font_size, "bold"), 
        fg=TEXT_COLOR, 
        bg=MAIN_BG_COLOR, 
        padx=LABEL_PADX, 
        pady=LABEL_PADY,
        wraplength=wrap_length_pixels,
        justify='center'
    )
    label.pack(expand=True, fill="both")

    notification_window.after(1500, notification_window.destroy)


def show_notification_top(message):
    """Ekranın üstünde bildirim gösterir."""
    global notification_window
    
    if not root:
        print("Hata: Tkinter ana penceresi (root) başlatılmamış.", file=sys.stderr)
        return

    if notification_window and notification_window.winfo_exists():
        notification_window.destroy()

    notification_window = tk.Toplevel(root)
    notification_window.overrideredirect(True)
    notification_window.attributes("-topmost", True)

    MAIN_BG_COLOR = "#2C3E50"
    BORDER_COLOR = "#FFD700"
    TEXT_COLOR = "#ECF0F1"
    
    FRAME_BORDER_THICKNESS = 6
    LABEL_PADX = 50
    LABEL_PADY = 40

    root.update_idletasks() 
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    notification_width = int(screen_width * 0.80)
    notification_height = int(screen_height * 0.15)
    
    x_pos = (screen_width // 2) - (notification_width // 2)
    y_pos = 0

    notification_window.geometry(f"{notification_width}x{notification_height}+{x_pos}+{y_pos}")

    total_horizontal_padding = (FRAME_BORDER_THICKNESS * 2) + (LABEL_PADX * 2)
    total_vertical_padding = (FRAME_BORDER_THICKNESS * 2) + (LABEL_PADY * 2)

    available_width = notification_width - total_horizontal_padding
    available_height = notification_height - total_vertical_padding
    
    font_size_in_pixels = int(available_height * 0.8)
    font_size_in_pixels = max(10, font_size_in_pixels)
    dynamic_font_size = -font_size_in_pixels

    wrap_length_pixels = max(1, available_width)

    main_frame = tk.Frame(notification_window, bg=BORDER_COLOR, padx=FRAME_BORDER_THICKNESS, pady=FRAME_BORDER_THICKNESS) 
    main_frame.pack(expand=True, fill="both")
    
    content_frame = tk.Frame(main_frame, bg=MAIN_BG_COLOR)
    content_frame.pack(expand=True, fill="both")

    label = tk.Label(
        content_frame, 
        text=message, 
        font=("Arial", dynamic_font_size, "bold"), 
        fg=TEXT_COLOR, 
        bg=MAIN_BG_COLOR, 
        padx=LABEL_PADX, 
        pady=LABEL_PADY,
        wraplength=wrap_length_pixels,
        justify='center'
    )
    label.pack(expand=True, fill="both")

    notification_window.after(1500, notification_window.destroy)


def update_text_box(message):
    """Ana metin kutusunu günceller."""
    text_box.config(state=tk.NORMAL)
    text_box.insert(tk.END, message + "\n")
    text_box.see(tk.END)
    text_box.config(state=tk.DISABLED)


def check_serial_queue():
    """Seri veri kuyruğunu kontrol eder ve komutları işler."""
    global ser, data_queue
    while data_queue:
        data = data_queue.pop(0)
        update_text_box(f"data came")
        if kurulum:
            if len(data) > 12:
                if data == id:
                    global auth
                    auth = True
                    update_text_box("Yetkilendirme başarılı")
                else:
                    auth = False
                    update_text_box("Yetkilendirme başarısız")
                    print(f"Yetkilendirme başarısız: {data}")
                    continue
            if auth:
                if data == "3217":
                    sil_function()
                elif data.startswith("31") and data.endswith("7") and auth == True:
                    value = int(data[2:-1])
                    print(f"Ortadaki değer: {value}")
                    try:
                        yukle_function(value*5)
                    except ValueError:
                        print(f"Geçersiz 'Yükle' komutu formatı: {data}")
                elif data.startswith("3567"):
                    try:
                        yukle_function(100)
                    except (IndexError, ValueError):
                        print(f"Geçersiz 'Yükle' komutu formatı: {data}")
                elif data.startswith("3131"):
                    try:
                        yukle_function(1)
                    except (IndexError, ValueError):
                        print(f"Geçersiz 'Yükle' komutu formatı: {data}")
                elif data.startswith("3687"):
                    try:
                        yukle_function(500)
                    except (IndexError, ValueError):
                        print(f"Geçersiz 'Yükle' komutu formatı: {data}")
                elif data == "3357":
                    toggle_brave()
                elif data == "4455":
                    kazanc_goster()
                else:
                    print(f"Bilinmeyen komut: {data}")
            else:
                update_text_box("Yetkilendirme başarısız, komut işlenemedi")
        else:
            update_text_box("Kurulum yapılmamış, komut işlenemedi. USB'den kurulum yapın.")
    root.after(10, check_serial_queue)


def close():
    update_text_box("Minimize edildi")
    root.iconify()


def kazanc_goster():
    """Kazanç bildirim penceresi gösterir."""
    global kazanc_window

    mysql_user = 'fungames'
    mysql_password = '7396Ksn!'
    database = 'fungames'
    
    try:
        connection = mysql.connector.connect(
            user=mysql_user,
            password=mysql_password,
            database=database,
            ssl_disabled=True
        )
        cursor = connection.cursor()

        extraTable = 'w_shops'
        extraColumn = 'balance'

        bakiye_query = "SELECT (SUM(money_in) - SUM(money_out)) FROM w_statistics_add"
        cursor.execute(bakiye_query)
        sonuc = cursor.fetchone()

        extra_sql_query = f"SELECT {extraColumn} FROM {extraTable}"
        cursor.execute(extra_sql_query)
        shop_bakiye_result = cursor.fetchone()
        shop_bakiye = shop_bakiye_result[0] if shop_bakiye_result else 0.0

        cursor.close()
        connection.close()

    except mysql.connector.Error as err:
        print(f"Veritabanı Hatası: {err}", file=sys.stderr)
        show_notification(f"Veritabanı Hatası:\n{err}")
        return
    except Exception as e:
        print(f"Beklenmedik Hata: {e}", file=sys.stderr)
        return

    if kazanc_window and kazanc_window.winfo_exists():
        kazanc_window.destroy()
        kazanc_window = None
        print("Kazanç penceresi kapatıldı.")
        return

    print("Kazanç penceresi açılıyor...")
    
    kazanc_window = tk.Toplevel(root)
    kazanc_window.overrideredirect(True)
    kazanc_window.attributes("-topmost", True)
    
    MAIN_BG_COLOR = "#2C3E50"
    BORDER_COLOR = "#FFD700"
    TEXT_COLOR = "#ECF0F1"
    
    FRAME_BORDER_THICKNESS = 6
    LABEL_PADX = 50
    LABEL_PADY = 40

    root.update_idletasks()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    kazanc_width = int(screen_width * 0.80)
    kazanc_height = int(screen_height * 0.25)
    
    x_pos = (screen_width // 2) - (kazanc_width // 2)
    y_pos = (screen_height // 2) - (kazanc_height // 2)

    kazanc_window.geometry(f"{kazanc_width}x{kazanc_height}+{x_pos}+{y_pos}")

    total_horizontal_padding = (FRAME_BORDER_THICKNESS * 2) + (LABEL_PADX * 2)
    total_vertical_padding = (FRAME_BORDER_THICKNESS * 2) + (LABEL_PADY * 2)

    available_width = max(1, kazanc_width - total_horizontal_padding)
    available_height = max(1, kazanc_height - total_vertical_padding)
    
    font_size_in_pixels = int(available_height * 0.4)
    font_size_in_pixels = max(10, font_size_in_pixels)
    dynamic_font_size = -font_size_in_pixels

    wrap_length_pixels = available_width

    main_frame = tk.Frame(kazanc_window, bg=BORDER_COLOR, padx=FRAME_BORDER_THICKNESS, pady=FRAME_BORDER_THICKNESS) 
    main_frame.pack(expand=True, fill="both")
    
    content_frame = tk.Frame(main_frame, bg=MAIN_BG_COLOR)
    content_frame.pack(expand=True, fill="both")

    def format_number(num):
        if num is None:
            return "0,00"
        try:
            num = float(num)
            formatted = f"{num:,.2f}"
            parts = formatted.split('.')
            integer_part = parts[0].replace(',', '.')
            decimal_part = parts[1] if len(parts) > 1 else "00"
            return f"{integer_part},{decimal_part}"
        except (ValueError, TypeError):
            return "Hata"

    formatted_shop_bakiye = format_number(shop_bakiye)
    formatted_sonuc = format_number(sonuc[0] if sonuc else 0.0)

    message_text = f"Kalan Limit: {formatted_shop_bakiye}\nNet Kazanç: {formatted_sonuc}"

    label = tk.Label(
        content_frame, 
        text=message_text, 
        font=("Arial", dynamic_font_size, "bold"),
        fg=TEXT_COLOR, 
        bg=MAIN_BG_COLOR, 
        padx=LABEL_PADX, 
        pady=LABEL_PADY,
        justify=tk.LEFT,
        wraplength=wrap_length_pixels
    )
    label.pack(expand=True, fill="both")


def on_app_close():
    """Uygulama kapatıldığında temizlik işlemlerini yapar."""
    global ser, app_running
    app_running = False
    if ser and ser.is_open:
        ser.close()
    root.destroy()


def pc_close():
    os.system("sudo /sbin/shutdown now")


def is_serial_alive(s):
    try:
        if not s or not s.is_open:
            return False
        s.in_waiting
        return True
    except:
        return False


def para_guncelle(eklenen_miktar):
    try:
        mysql_user = 'fungames'
        mysql_password = '7396Ksn!'
        database = 'fungames'

        user_table = 'w_users'
        user_column = 'balance'
        count_balance_column = 'count_balance'
        count_refunds_column = 'count_refunds'
        userId = 320

        extraTable = 'w_shops'
        extraColumn = 'balance'
        extraValue = eklenen_miktar
        count_refunds_increase = eklenen_miktar * 0.1

        connection = mysql.connector.connect(
            user=mysql_user,
            password=mysql_password,
            database=database,
            ssl_disabled=True
        )
        cursor = connection.cursor()
        
        shop_bakiye_sorgu = f"SELECT {extraColumn} FROM {extraTable}"
        cursor.execute(shop_bakiye_sorgu)
        shop_bakiye = cursor.fetchone()[0]

        if shop_bakiye < eklenen_miktar:
            update_text_box("Bakiye yetersiz")
            show_notification("LİMİT YETERSİZ. LİMİTİ ARTIRIN.")
            return False
            
        sql_query = f"UPDATE {user_table} SET {user_column} = {user_column} + {eklenen_miktar}, {count_balance_column} = {count_balance_column} + {eklenen_miktar} WHERE id = {userId}"
        cursor.execute(sql_query)
        
        extra_sql_query = f"UPDATE {extraTable} SET {extraColumn} = {extraColumn} - {extraValue}"
        cursor.execute(extra_sql_query)
        
        cursor.execute("SELECT MAX(statistic_id) FROM w_statistics_add")
        max_statistic_id = cursor.fetchone()[0]
        if max_statistic_id is None:
            max_statistic_id = 0

        next_statistic_id = max_statistic_id + 1
        
        add_statistics_query = f"INSERT INTO w_statistics_add (statistic_id, credit_out, money_in, user_id, shop_id) VALUES ({next_statistic_id}, {eklenen_miktar}, {eklenen_miktar}, {userId}, 1)"
        cursor.execute(add_statistics_query)
        
        update_statistics_query = f"INSERT INTO w_statistics (sum, old, user_id, shop_id, updated_at, payeer_id, `system`) VALUES ({eklenen_miktar}, 0.0000, {userId}, 1, NOW(), 294, 'handpay') ON DUPLICATE KEY UPDATE sum = sum + {eklenen_miktar}, old = 0.0000"
        cursor.execute(update_statistics_query)
        
        connection.commit()
        print("Güncelleme işlemi tamamlandı.")
        return True

    except mysql.connector.Error as error:
        print("Hata:", error)
        return False

    except ValueError as error:
        print("Hata:", error)
        return False
    
    except Exception as error:
        print("Beklenmeyen hata:", error)
        return False

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


def get_computer_id():
    import subprocess, hashlib
    try:
        result = subprocess.check_output("wmic csproduct get uuid", shell=True).decode()
        uuid = result.split("\n")[1].strip()
    except:
        result = subprocess.check_output("cat /etc/machine-id", shell=True).decode()
        uuid = result.strip()
    return hashlib.sha256(uuid.encode()).hexdigest()[:14]


def para_sil():
    try:
        mysql_user = 'fungames'
        mysql_password = '7396Ksn!'
        database = 'fungames'

        userId = 320

        connection = mysql.connector.connect(
            user=mysql_user,
            password=mysql_password,
            database=database,
            ssl_disabled=True
        )
        cursor = connection.cursor()

        select_balance_query = f"SELECT balance FROM w_users WHERE id = {userId}"
        cursor.execute(select_balance_query)
        user_balance = cursor.fetchone()[0]

        user_table = 'w_users'
        user_column = 'balance'
        count_balance_column = 'count_balance'
        count_refunds_column = 'count_refunds'

        extraTable = 'w_shops'
        extraColumn = 'balance'

        sql_query = f"UPDATE {user_table} SET {user_column} = 0, {count_balance_column} = 0, {count_refunds_column} = 0 WHERE id = {userId}"
        cursor.execute(sql_query)

        extra_sql_query = f"UPDATE {extraTable} SET {extraColumn} = {extraColumn} + {user_balance}"
        cursor.execute(extra_sql_query)

        cursor.execute("SELECT IFNULL(MAX(statistic_id), 0) FROM w_statistics_add")
        max_statistic_id = cursor.fetchone()[0]
        next_statistic_id = max_statistic_id + 1

        add_statistics_query = f"INSERT INTO w_statistics_add (statistic_id, credit_in, money_out, user_id, shop_id) VALUES ({next_statistic_id}, {user_balance}, {user_balance}, {userId}, 1)"
        cursor.execute(add_statistics_query)

        update_statistics_query = f"INSERT INTO w_statistics (sum, old, user_id, shop_id, updated_at, payeer_id, `system`, type) VALUES (-{user_balance}, 0.0000, {userId}, 1, NOW(), 294, 'handpay', 'out') ON DUPLICATE KEY UPDATE sum = sum - {user_balance}, old = 0.0000"
        cursor.execute(update_statistics_query)

        connection.commit()
        print("İşlem tamamlandı: Kullanıcının tüm kredisi sıfırlandı.")

    except mysql.connector.Error as error:
        print("Hata:", error)

    except ValueError as error:
        print("Hata:", error)

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


def arduino_monitor():
    global ser, app_running
    while app_running:
        if not is_serial_alive(ser):
            port = find_arduino_port(ARDUINO_VID, ARDUINO_PID)
            if port:
                try:
                    ser = serial.Serial(port, 9600, timeout=1)
                    update_text_box("Cihaz yeniden bağlandı")
                    serial_thread = threading.Thread(target=read_serial_data, daemon=True)
                    serial_thread.start()
                except serial.SerialException as e:
                    print(f"Port açma hatası (yeniden bağlanma): {e}")
                    ser = None
        time.sleep(2)


# --- Ana Uygulama Kurulumu ---
root = tk.Tk()
root.title("Device Communication [TEST MODE]")
root.geometry("300x400")

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
x = (screen_width // 2) - (400 // 2)
y = (screen_height // 2) - (200 // 2)
root.geometry(f"+{x}+{y}")

root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(0, weight=1)

text_box = tk.Text(root, height=5, width=30, font=("Inter", 12), bd=2, relief="solid", wrap="word")
text_box.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
update_text_box("[TEST MODU]")
update_text_box("Program başladı")
text_box.config(state=tk.DISABLED)

# Seri iletişimi başlat
port = find_arduino_port(ARDUINO_VID, ARDUINO_PID)
if port:
    try:
        ser = serial.Serial(port, 9600, timeout=1)
        print(f"Arduino bağlandı: {port}")
        serial_thread = threading.Thread(target=read_serial_data, daemon=True)
        serial_thread.start()
    except serial.SerialException as e:
        print(f"Arduino'ya bağlanılamadı: {e}")
        update_text_box("Device Error")
else:
    update_text_box("Device Error - mock_arduino çalıştırın")

if kurulum:
    if str(get_computer_id()) != str(id):
        print(f"ID uyuşmuyor: {get_computer_id()} != {id}")
        update_text_box("Yetkilendirme başarısız")
        # TEST MODU: Bilgisayarı kapatma
        # root.after(1000, pc_close)
else:
    update_text_box("Kurulum yapılmamış, USB'den kurulum yapın.")

arduino_thread = threading.Thread(target=arduino_monitor, daemon=True)
arduino_thread.start()

root.after(10, check_serial_queue)
root.after(3000, check_balance_for_game)
root.after(2000, close)
root.protocol("WM_DELETE_WINDOW", on_app_close)

root.mainloop()
