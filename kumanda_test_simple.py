#!/usr/bin/env python3
"""
kumanda_test_simple.py - Basitleştirilmiş Test Versiyonu

MySQL bağımlılığı olmadan mock Arduino ile iletişimi test eder.
Sadece seri port iletişimini ve komut işlemeyi test eder.

KULLANIM:
1. Terminal 1: python3 mock_arduino_socat.py
2. Terminal 2: python3 kumanda_test_simple.py
"""

import tkinter as tk
import serial
import threading
import time
import sys
import os

# --- TEST AYARLARI ---
VIRTUAL_PORT = "/tmp/ttyVirtual1"
BAUD_RATE = 9600

# --- Global Değişkenler ---
ser = None
data_queue = []
app_running = True
notification_window = None
auth = False  # Yetkilendirme durumu
expected_auth_id = None  # Beklenen yetkilendirme ID'si


def get_computer_id():
    """Bilgisayar ID'sini hesaplar (kumanda.py ile aynı)."""
    import subprocess, hashlib
    try:
        result = subprocess.check_output("wmic csproduct get uuid", shell=True).decode()
        uuid = result.split("\n")[1].strip()
    except:
        result = subprocess.check_output("cat /etc/machine-id", shell=True).decode()
        uuid = result.strip()
    return hashlib.sha256(uuid.encode()).hexdigest()[:14]


def is_serial_alive(s):
    """Seri port bağlantısını kontrol eder."""
    try:
        if not s or not s.is_open:
            return False
        s.in_waiting
        return True
    except:
        return False


def read_serial_data():
    """Seri porttan verileri okur."""
    global ser, data_queue, app_running
    while app_running:
        if is_serial_alive(ser):
            try:
                if ser.in_waiting > 0:
                    data = ser.readline().decode('utf-8').strip()
                    if data:
                        data_queue.append(data)
                        print(f"[SERİ] Alındı: '{data}'")
            except serial.SerialException as e:
                print(f"[HATA] Seri port hatası: {e}")
                ser = None
            except Exception as e:
                print(f"[HATA] Okuma hatası: {e}")
        time.sleep(0.05)


def send_to_arduino(command_str):
    """Arduino'ya komut gönderir."""
    global ser
    if is_serial_alive(ser):
        try:
            ser.write(f"{command_str}\n".encode('utf-8'))
            print(f"[SERİ] Gönderildi: '{command_str}'")
        except Exception as e:
            print(f"[HATA] Yazma hatası: {e}")
    else:
        print("[HATA] Seri port bağlı değil!")


def show_notification(message):
    """Basit bildirim penceresi gösterir."""
    global notification_window
    
    if notification_window and notification_window.winfo_exists():
        notification_window.destroy()

    notification_window = tk.Toplevel(root)
    notification_window.overrideredirect(True)
    notification_window.attributes("-topmost", True)

    # Boyut ve konum
    width = 600
    height = 150
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    
    notification_window.geometry(f"{width}x{height}+{x}+{y}")
    notification_window.configure(bg="#FFD700")

    frame = tk.Frame(notification_window, bg="#2C3E50", padx=5, pady=5)
    frame.pack(expand=True, fill="both", padx=5, pady=5)

    label = tk.Label(
        frame,
        text=message,
        font=("Arial", 24, "bold"),
        fg="#ECF0F1",
        bg="#2C3E50"
    )
    label.pack(expand=True, fill="both")

    print(f"[BİLDİRİM] {message}")
    notification_window.after(2000, notification_window.destroy)


def update_log(message):
    """Log kutusunu günceller."""
    log_text.config(state=tk.NORMAL)
    log_text.insert(tk.END, message + "\n")
    log_text.see(tk.END)
    log_text.config(state=tk.DISABLED)


def process_commands():
    """Gelen komutları işler."""
    global auth, expected_auth_id
    
    while data_queue:
        data = data_queue.pop(0)
        update_log(f"Veri: {data}")
        
        # Yetkilendirme kontrolü (uzun veri = potansiyel auth ID)
        if len(data) > 12:
            if data == expected_auth_id:
                auth = True
                update_log("✓ Yetkilendirme BAŞARILI")
                show_notification("YETKİLENDİRME BAŞARILI")
            else:
                auth = False
                update_log(f"✗ Yetkilendirme BAŞARISIZ")
                update_log(f"  Beklenen: {expected_auth_id}")
                update_log(f"  Gelen: {data}")
            continue
        
        # Komut işleme (sadece auth'dan sonra)
        if not auth:
            update_log("⚠ Yetkilendirme bekleniyor...")
            continue
        
        # Komutları işle
        if data == "3217":
            update_log("→ SİL komutu alındı")
            show_notification("SİLİNDİ")
            send_to_arduino("OK_SIL")
            
        elif data.startswith("31") and data.endswith("7"):
            try:
                value = int(data[2:-1])
                amount = value * 5
                update_log(f"→ YÜKLE komutu: {amount} TL")
                show_notification(f"{amount} TL YÜKLENDİ")
                send_to_arduino(f"OK_YUKLE_{amount}")
            except ValueError:
                update_log(f"✗ Geçersiz yükle formatı: {data}")
                
        elif data == "3567":
            update_log("→ YÜKLE komutu: 100 TL")
            show_notification("100 TL YÜKLENDİ")
            send_to_arduino("OK_YUKLE_100")
            
        elif data == "3131":
            update_log("→ YÜKLE komutu: 1 TL")
            show_notification("1 TL YÜKLENDİ")
            send_to_arduino("OK_YUKLE_1")
            
        elif data == "3687":
            update_log("→ YÜKLE komutu: 500 TL")
            show_notification("500 TL YÜKLENDİ")
            send_to_arduino("OK_YUKLE_500")
            
        elif data == "3357":
            update_log("→ OYUN komutu alındı")
            show_notification("OYUN AÇ/KAPAT")
            send_to_arduino("OK_OYUN")
            
        elif data == "4455":
            update_log("→ KAZANÇ komutu alındı")
            show_notification("KAZANÇ: 1234.56 TL")
            send_to_arduino("OK_KAZANC")
            
        else:
            update_log(f"? Bilinmeyen komut: {data}")
    
    root.after(50, process_commands)


def connect_serial():
    """Seri porta bağlanır."""
    global ser
    
    if not os.path.exists(VIRTUAL_PORT):
        update_log(f"HATA: {VIRTUAL_PORT} bulunamadı")
        update_log("Önce mock_arduino_socat.py çalıştırın!")
        return False
    
    try:
        ser = serial.Serial(VIRTUAL_PORT, BAUD_RATE, timeout=0.1)
        update_log(f"Bağlandı: {VIRTUAL_PORT}")
        return True
    except serial.SerialException as e:
        update_log(f"Bağlantı hatası: {e}")
        return False


def monitor_connection():
    """Bağlantıyı izler ve gerekirse yeniden bağlanır."""
    global ser
    
    if not is_serial_alive(ser):
        update_log("Bağlantı kesildi, yeniden bağlanılıyor...")
        if connect_serial():
            # Okuma thread'ini yeniden başlat
            read_thread = threading.Thread(target=read_serial_data, daemon=True)
            read_thread.start()
    
    root.after(2000, monitor_connection)


def on_close():
    """Uygulama kapatılırken çağrılır."""
    global app_running, ser
    app_running = False
    if ser and ser.is_open:
        ser.close()
    root.destroy()


# --- GUI Oluştur ---
root = tk.Tk()
root.title("Kumanda Test [MySQL'siz]")
root.geometry("500x400")

# Bilgi etiketi
info_frame = tk.Frame(root, bg="#2C3E50", padx=10, pady=5)
info_frame.pack(fill="x")

info_label = tk.Label(
    info_frame,
    text="Mock Arduino Test Modu",
    font=("Arial", 14, "bold"),
    fg="#FFD700",
    bg="#2C3E50"
)
info_label.pack()

# Beklenen ID
expected_auth_id = get_computer_id()
id_label = tk.Label(
    info_frame,
    text=f"Beklenen Auth ID: {expected_auth_id}",
    font=("Arial", 10),
    fg="#ECF0F1",
    bg="#2C3E50"
)
id_label.pack()

# Durum etiketi
status_var = tk.StringVar(value="Bağlanıyor...")
status_label = tk.Label(
    root,
    textvariable=status_var,
    font=("Arial", 12),
    fg="#666"
)
status_label.pack(pady=5)

# Log kutusu
log_frame = tk.Frame(root)
log_frame.pack(expand=True, fill="both", padx=10, pady=10)

scrollbar = tk.Scrollbar(log_frame)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

log_text = tk.Text(
    log_frame,
    height=15,
    width=60,
    font=("Consolas", 10),
    yscrollcommand=scrollbar.set
)
log_text.pack(side=tk.LEFT, expand=True, fill="both")
scrollbar.config(command=log_text.yview)
log_text.config(state=tk.DISABLED)

# Başlat
update_log("=" * 50)
update_log("KUMANDA TEST - MySQL'siz Basit Versiyon")
update_log("=" * 50)
update_log("")

# Bağlan
if connect_serial():
    status_var.set("✓ Bağlı")
    status_label.config(fg="green")
    
    # Okuma thread'ini başlat
    read_thread = threading.Thread(target=read_serial_data, daemon=True)
    read_thread.start()
else:
    status_var.set("✗ Bağlantı Yok")
    status_label.config(fg="red")

# Periyodik kontroller
root.after(50, process_commands)
root.after(2000, monitor_connection)

# Kapatma protokolü
root.protocol("WM_DELETE_WINDOW", on_close)

update_log("Mock Arduino'dan komut bekleniyor...")
update_log("(Önce 'auth' komutu gönderilmelidir)")
update_log("")

root.mainloop()
