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

# --- Yapılandırma ---
# Arduino Uno'nuzun Sabit VID ve PID değerleri
ARDUINO_VID = ["1A86", "2341"]
ARDUINO_PID = ["7523", "8037"]

# Brave tarayıcısının işletim sisteminize göre varsayılan yolları
# Eğer Brave farklı bir yere kuruluysa bu yolları güncellemeniz gerekebilir.
BRAVE_PATH = {
    "Windows": r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    "Darwin": "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser", # macOS
    "Linux": "/usr/bin/brave-browser" # Yaygın Linux yolu
}

KEY_B64 = b"o3QqhjSBDaIEhd8h_e8icgou0socOWYTG9S_eFIALo0="
F = Fernet(KEY_B64)

# --- Global Değişkenler ---
ser = None # Seri port nesnesi
data_queue = [] # Seri porttan gelen verileri depolamak için kuyruk (thread'ler arası iletişim)
app_running = True # Seri okuma thread'ini kontrol etmek için bayrak
notification_window = None # Bildirim penceresini takip etmek için
auth = False # Yetkilendirme durumu,
kurulum = False # Kurulum durumu
id = None # Yetkilendirme için kullanılan ID
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



#linux: 2a049cc583f34f windows: 252592dddf04cf
# --- Seri İletişim Fonksiyonları ---
def find_arduino_port(vid_list, pid_list):
    """Belirtilen VID ve PID listelerinden birine sahip Arduino'nun seri portunu bulur."""
    ports = serial.tools.list_ports.comports()

    # Tek bir değer verilirse liste haline getir
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
            # Komutun sonuna newline (\n) ekleyerek gönder
            # Arduino'da 'readStringUntil('\n')' ile okuyabilirsin
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
                    # Seri porttan bir satır oku ve UTF-8 olarak decode et
                    data = ser.readline().decode('utf-8').strip()
                    data_queue.append(data) # Veriyi kuyruğa ekle
                    print(f"Alındı: {data}") # Hata ayıklama için konsola yaz
            except serial.SerialException as e:
                print(f"Seri port hatası: {e}")
                # Bağlantıyı yeniden kurmaya çalış veya kullanıcıya bildir
                ser = None # Bağlantının kesildiğini işaretle
            except Exception as e:
                print(f"Seri okuma thread'inde beklenmeyen hata: {e}")
        time.sleep(0.1) # CPU kullanımını azaltmak için küçük bir gecikme

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
            connection_timeout=5 # Hata olursa 5 saniyede vazgeç
        )
        cursor = connection.cursor()
        cursor.execute(f"SELECT balance FROM w_users WHERE id = {userId}")
        result = cursor.fetchone()
        
        if result:
            return float(result[0]) # Bakiyeyi float olarak döndür
        else:
            return None # Kullanıcı bulunamazsa
            
    except Exception as e:
        print(f"Bakiye okuma hatası: {e}")
        return None # Hata durumunda None döndür
    finally:
        # 'connection' değişkeninin tanımlandığından ve bağlı olduğundan emin ol
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

# --- Komut Fonksiyonları ---
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
    """
    Bakiyeyi periyodik olarak kontrol eder.
    Sadece PHP tarafından yapılan harcamaları (oyun oynama) yakalar.
    """
    global last_known_balance
    
    current_balance = get_current_balance()
    
    if current_balance is None:
        # Veritabanına bağlanamadık, bir sonraki denemeyi bekle
        print("Bakiye kontrolü başarısız (DB hatası?), 3 saniye sonra tekrar denenecek.")
        root.after(3000, check_balance_for_game) # Hata varsa biraz daha bekle
        return

    # İlk çalıştırma: Henüz 'last_known_balance' ayarlanmamış
    if last_known_balance is None:
        last_known_balance = current_balance
        print(f"Başlangıç bakiyesi ayarlandı: {last_known_balance}")
    
    # ----------------------------------------------------
    # ANA LOGİK BURADA
    # ----------------------------------------------------
    elif current_balance < last_known_balance:
        # Bakiye DÜŞMÜŞ!
        
        # Senin kuralın: "0'sa göndermesin" (para_sil komutunu es geç)
        if current_balance == 0:
            print(f"Bakiye sıfırlandı (para_sil). Arduino'ya sinyal GÖNDERİLMEDİ.")
        else:
            # Bakiye 0 değil ama ESKİSİNDEN AZ. Demek ki PHP'de oyun oynandı!
            print(f"HARCAMA TESPİT EDİLDİ! Eski: {last_known_balance}, Yeni: {current_balance}")
            show_notification_top("Sakızınız Afiyet Olsun! İyi Eğlenceler...")
            # Arduino'ya oyunun oynandığına dair bir sinyal gönder
            send_to_arduino("111111") # Buraya istediğin komutu yazabilirsin
        
        # Yeni bakiyeyi 'eski' olarak güncelle
        last_known_balance = current_balance
        
    elif current_balance > last_known_balance:
        # Bakiye YÜKSELMİŞ (Muhtemelen para_guncelle çalıştı)
        print(f"Bakiye artışı tespit edildi (para_guncelle).")
        last_known_balance = current_balance
    
    # else: current_balance == last_known_balance (Değişiklik yok)
    
    # ----------------------------------------------------
    # 1 saniye sonra tekrar kontrol et
    root.after(1000, check_balance_for_game)

def toggle_brave():
    """Brave tarayıcısını açar veya kapatır (açıksa kapatır, kapalıysa açar)."""
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


# --- GUI Fonksiyonları ---

def show_notification(message):
    """
    Ekran çözünürlüğüne duyarlı, ölçeklenebilir bir bildirim penceresi gösterir.
    
    Yazı tipi boyutu ve metin kaydırma, pencerenin boyutuna göre dinamik olarak ayarlanır.
    """
    global notification_window
    
    # Eğer root penceresi oluşturulmamışsa, hata verip çık.
    if not root:
        print("Hata: Tkinter ana penceresi (root) başlatılmamış.", file=sys.stderr)
        return

    # 1. Önceki bildirimi yok et (Eğer varsa)
    if notification_window and notification_window.winfo_exists():
        notification_window.destroy()

    # 2. Yeni Toplevel penceresini oluştur
    notification_window = tk.Toplevel(root)
    notification_window.overrideredirect(True)  # Pencere kenarlıklarını kaldır
    notification_window.attributes("-topmost", True)  # Her zaman en üstte

    # --- Estetik Stil Ayarları ---
    MAIN_BG_COLOR = "#2C3E50"  # Koyu mavi
    BORDER_COLOR = "#FFD700"  # Altın Sarısı
    TEXT_COLOR = "#ECF0F1"  # Açık yazı rengi
    
    # --- Dinamik Boyutlandırma için Sabitler ---
    # Bu değerler, padding'lerinizle eşleşmeli
    FRAME_BORDER_THICKNESS = 6  # main_frame'in padx/pady değeri
    LABEL_PADX = 50             # label'ın padx değeri
    LABEL_PADY = 40             # label'ın pady değeri

    # 3. Boyut ve Konum Hesaplama (Pencereyi oluşturmadan ÖNCE)
    # Ekran boyutlarını doğru alabilmek için
    root.update_idletasks() 
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Pencere Boyutları: Ekranın yüzdesi
    notification_width = int(screen_width * 0.80)
    notification_height = int(screen_height * 0.25)
    
    # Konum: Tam ortalama
    x_pos = (screen_width // 2) - (notification_width // 2)
    y_pos = (screen_height // 2) - (notification_height // 2)

    # Pencereyi ayarla
    notification_window.geometry(f"{notification_width}x{notification_height}+{x_pos}+{y_pos}")

    # 4. Yazı Tipi ve Metin Kaydırma için Alan Hesaplaması
    
    # Toplam yatay dolgu (çerçeve solu/sağı + etiket solu/sağı)
    total_horizontal_padding = (FRAME_BORDER_THICKNESS * 2) + (LABEL_PADX * 2)
    # Toplam dikey dolgu (çerçeve üstü/altı + etiket üstü/altı)
    total_vertical_padding = (FRAME_BORDER_THICKNESS * 2) + (LABEL_PADY * 2)

    # Metnin sığması gereken gerçek genişlik
    # wraplength için kullanılır
    available_width = notification_width - total_horizontal_padding
    # Metnin sığması gereken gerçek yükseklik
    # font boyutu için kullanılır
    available_height = notification_height - total_vertical_padding
    
    # --- Dinamik Font Boyutu Hesaplama ---
    # Fontun, mevcut dikey alanın %80'ini kaplamasını hedefleyelim.
    # Negatif değer, Tkinter'e font boyutunu 'piksel' olarak belirtir.
    # Bu, 'point' biriminden çok daha güvenilirdir.
    font_size_in_pixels = int(available_height * 0.8)
    
    # Çok küçük olmasını engelle (en az 10px)
    font_size_in_pixels = max(10, font_size_in_pixels)
    
    # Tkinter font tuple'ı için piksel cinsinden boyut (negatif sayı)
    dynamic_font_size = -font_size_in_pixels

    # --- Metin Kaydırma (Wraplength) Hesaplama ---
    # Metnin, mevcut yatay alandan taşmamasını sağlar.
    # 1'den küçük olmamalı.
    wrap_length_pixels = max(1, available_width)

    # 5. Altın Sarısı Çerçeve
    main_frame = tk.Frame(notification_window, bg=BORDER_COLOR, padx=FRAME_BORDER_THICKNESS, pady=FRAME_BORDER_THICKNESS) 
    main_frame.pack(expand=True, fill="both")
    
    # 6. Ana İçerik Alanı
    content_frame = tk.Frame(main_frame, bg=MAIN_BG_COLOR)
    content_frame.pack(expand=True, fill="both")

    # 7. Dinamik Olarak Boyutlandırılmış Mesaj Etiketi
    label = tk.Label(
        content_frame, 
        text=message, 
        font=("Arial", dynamic_font_size, "bold"), 
        fg=TEXT_COLOR, 
        bg=MAIN_BG_COLOR, 
        padx=LABEL_PADX, 
        pady=LABEL_PADY,
        # YENİ EKLENEN ÖZELLİKLER:
        wraplength=wrap_length_pixels, # Metni yatayda kaydır
        justify='center'                # Kaydırılan metni ortala
    )
    label.pack(expand=True, fill="both")

    # 8. Kapanma Süresi
    notification_window.after(1500, notification_window.destroy)

def show_notification_top(message):
    """
    Ekran çözünürlüğüne duyarlı, ölçeklenebilir bir bildirim penceresi gösterir.
    Ekranın yatayda ortasında ve dikeyde en üstünde belirir.
    
    Yazı tipi boyutu ve metin kaydırma, pencerenin boyutuna göre dinamik olarak ayarlanır.
    """
    global notification_window
    
    # Varsayılan global değişkenlerin (root, sys, tk) tanımlı olduğunu varsayıyoruz.
    import sys 
    import tkinter as tk 
    # Not: root değişkeninin dışarıda tk.Tk() ile oluşturulması gerekir.
    
    # Eğer root penceresi oluşturulmamışsa, hata verip çık.
    if not root:
        print("Hata: Tkinter ana penceresi (root) başlatılmamış.", file=sys.stderr)
        return

    # 1. Önceki bildirimi yok et (Eğer varsa)
    if notification_window and notification_window.winfo_exists():
        notification_window.destroy()

    # 2. Yeni Toplevel penceresini oluştur
    notification_window = tk.Toplevel(root)
    notification_window.overrideredirect(True)  # Pencere kenarlıklarını kaldır
    notification_window.attributes("-topmost", True)  # Her zaman en üstte

    # --- Estetik Stil Ayarları ---
    MAIN_BG_COLOR = "#2C3E50"  # Koyu mavi
    BORDER_COLOR = "#FFD700"  # Altın Sarısı
    TEXT_COLOR = "#ECF0F1"  # Açık yazı rengi
    
    # --- Dinamik Boyutlandırma için Sabitler ---
    # Bu değerler, padding'lerinizle eşleşmeli
    FRAME_BORDER_THICKNESS = 6  # main_frame'in padx/pady değeri
    LABEL_PADX = 50             # label'ın padx değeri
    LABEL_PADY = 40             # label'ın pady değeri

    # 3. Boyut ve Konum Hesaplama (Pencereyi oluşturmadan ÖNCE)
    # Ekran boyutlarını doğru alabilmek için
    root.update_idletasks() 
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight() # Bu değişken kullanılmıyor ama kalsın

    # Pencere Boyutları: Ekranın yüzdesi
    # Orijinal kodda ekranın %80'i genişlik ve %25'i yükseklik kullanılıyordu.
    notification_width = int(screen_width * 0.80)
    # Bildirimler genelde daha ince olur. Yüksekliği azaltabiliriz:
    notification_height = int(screen_height * 0.15) 
    
    # Konum HESAPLAMA: 🎯
    # ----------------------------------------------------------------
    # X Konumu: Yatayda Tam ortalama
    x_pos = (screen_width // 2) - (notification_width // 2)
    
    # Y Konumu: Ekranın En Üstü (y=0)
    y_pos = 0  
    # ----------------------------------------------------------------

    # Pencereyi ayarla
    notification_window.geometry(f"{notification_width}x{notification_height}+{x_pos}+{y_pos}")

    # 4. Yazı Tipi ve Metin Kaydırma için Alan Hesaplaması
    
    # Toplam yatay dolgu (çerçeve solu/sağı + etiket solu/sağı)
    total_horizontal_padding = (FRAME_BORDER_THICKNESS * 2) + (LABEL_PADX * 2)
    # Toplam dikey dolgu (çerçeve üstü/altı + etiket üstü/altı)
    total_vertical_padding = (FRAME_BORDER_THICKNESS * 2) + (LABEL_PADY * 2)

    # Metnin sığması gereken gerçek genişlik
    available_width = notification_width - total_horizontal_padding
    # Metnin sığması gereken gerçek yükseklik
    available_height = notification_height - total_vertical_padding
    
    # --- Dinamik Font Boyutu Hesaplama ---
    font_size_in_pixels = int(available_height * 0.8)
    
    # Çok küçük olmasını engelle (en az 10px)
    font_size_in_pixels = max(10, font_size_in_pixels)
    
    # Tkinter font tuple'ı için piksel cinsinden boyut (negatif sayı)
    dynamic_font_size = -font_size_in_pixels

    # --- Metin Kaydırma (Wraplength) Hesaplama ---
    # Metnin, mevcut yatay alandan taşmamasını sağlar.
    wrap_length_pixels = max(1, available_width)

    # 5. Altın Sarısı Çerçeve
    main_frame = tk.Frame(notification_window, bg=BORDER_COLOR, padx=FRAME_BORDER_THICKNESS, pady=FRAME_BORDER_THICKNESS) 
    main_frame.pack(expand=True, fill="both")
    
    # 6. Ana İçerik Alanı
    content_frame = tk.Frame(main_frame, bg=MAIN_BG_COLOR)
    content_frame.pack(expand=True, fill="both")

    # 7. Dinamik Olarak Boyutlandırılmış Mesaj Etiketi
    label = tk.Label(
        content_frame, 
        text=message, 
        font=("Arial", dynamic_font_size, "bold"), 
        fg=TEXT_COLOR, 
        bg=MAIN_BG_COLOR, 
        padx=LABEL_PADX, 
        pady=LABEL_PADY,
        # YENİ EKLENEN ÖZELLİKLER:
        wraplength=wrap_length_pixels, # Metni yatayda kaydır
        justify='center'                # Kaydırılan metni ortala
    )
    label.pack(expand=True, fill="both")

    # 8. Kapanma Süresi
    notification_window.after(1500, notification_window.destroy)


def update_text_box(message):
    """Ana metin kutusunu günceller."""
    text_box.config(state=tk.NORMAL) # Yazılabilir yap
    # Yeni mesajı mevcut içeriğe ekle ve yeni bir satıra geç
    text_box.insert(tk.END, message + "\n")
    text_box.see(tk.END) # En son eklenen metni görünür yap (otomatik kaydırma)
    text_box.config(state=tk.DISABLED) # Salt okunur yap

def check_serial_queue():
    """Seri veri kuyruğunu kontrol eder ve komutları işler."""
    global ser, data_queue
    while data_queue:
        data = data_queue.pop(0) # Kuyruktan bir veri al
        update_text_box(f"data came") # Ana metin kutusunu güncelle, gelen datayı da göster
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
                    value = int(data[2:-1])  # 3. karakterden başla, sondan 1 çıkar
                    print(f"Ortadaki değer: {value}")
                    try:
                        yukle_function(value*5)
                    except ValueError:
                        print(f"Geçersiz 'Yükle' komutu formatı: {data}")
                elif data.startswith("3567"):
                    try:
                        '''
                        value_str = data.split(" ")[1] # "Yükle " sonrası değeri al
                        value = int(value_str) # Değeri tamsayıya çevir
                        '''
                        yukle_function(100)
                    except (IndexError, ValueError):
                        print(f"Geçersiz 'Yükle' komutu formatı: {data}")
                elif data.startswith("3131"):
                    try:
                        '''
                        value_str = data.split(" ")[1] # "Yükle " sonrası değeri al
                        value = int(value_str) # Değeri tamsayıya çevir
                        '''
                        yukle_function(1)
                    except (IndexError, ValueError):
                        print(f"Geçersiz 'Yükle' komutu formatı: {data}")
                elif data.startswith("3687"):
                    try:
                        '''
                        value_str = data.split(" ")[1] # "Yükle " sonrası değeri al
                        value = int(value_str) # Değeri tamsayıya çevir
                        '''
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
    root.after(10, check_serial_queue) # 100ms sonra tekrar kontrol et
def close():
    update_text_box("Minimize edildi")
    root.iconify()
def kazanc_goster():
    """
    Ekran çözünürlüğüne duyarlı, ölçeklenebilir bir kazanç bildirim penceresi gösterir.
    
    Yazı tipi boyutu ve metin kaydırma, pencerenin boyutuna göre dinamik olarak ayarlanır.
    """
    global kazanc_window

    # --- Veritabanı İşlemleri ---
    # Gerçek uygulamada, bu bilgileri güvenli bir yerden okuyun
    mysql_user = 'fungames'
    mysql_password = '7396Ksn!'
    database = 'fungames'
    
    try:
        # MySQL bağlantısı oluşturma (SSL olmadan)
        connection = mysql.connector.connect(
            user=mysql_user,
            password=mysql_password,
            database=database,
            ssl_disabled=True  # SSL olmadan bağlan
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
        # Hata durumunda da bir bildirim gösterebiliriz
        show_notification(f"Veritabanı Hatası:\n{err}") # Diğer fonksiyonu çağır
        return
    except Exception as e:
        print(f"Beklenmedik Hata: {e}", file=sys.stderr)
        return

    # --- Pencere Geçiş (Toggle) Mantığı ---
    if kazanc_window and kazanc_window.winfo_exists():
        kazanc_window.destroy()
        kazanc_window = None # Referansı temizle
        print("Kazanç penceresi kapatıldı.")
        return

    # Eğer pencere kapalıysa, yeni pencereyi aç.
    print("Kazanç penceresi açılıyor...")
    
    # Yeni Toplevel penceresini oluştur
    kazanc_window = tk.Toplevel(root)
    kazanc_window.overrideredirect(True)  # Pencere kenarlıklarını kaldır
    kazanc_window.attributes("-topmost", True)  # Her zaman en üstte tut
    
    # --- Estetik Stil Ayarları ---
    MAIN_BG_COLOR = "#2C3E50"  # Modern koyu mavi ton
    BORDER_COLOR = "#FFD700"  # Altın Sarısı
    TEXT_COLOR = "#ECF0F1"    # Açık yazı rengi
    
    # --- Dinamik Boyutlandırma için Sabitler ---
    FRAME_BORDER_THICKNESS = 6  # main_frame'in padx/pady değeri
    LABEL_PADX = 50             # label'ın padx değeri
    LABEL_PADY = 40             # label'ın pady değeri

    # 1. Boyut ve Konum Hesaplama (Widget'ları oluşturmadan ÖNCE)
    root.update_idletasks() # Ekran boyutlarını doğru alabilmek için
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Pencere Boyutları: Ekranın yüzdesi
    kazanc_width = int(screen_width * 0.80)
    kazanc_height = int(screen_height * 0.25) 
    
    # Konum: Tam ortalama
    x_pos = (screen_width // 2) - (kazanc_width // 2)
    y_pos = (screen_height // 2) - (kazanc_height // 2)

    # Pencereyi ayarla (geometriyi *önce* ayarla)
    kazanc_window.geometry(f"{kazanc_width}x{kazanc_height}+{x_pos}+{y_pos}")

    # 2. Yazı Tipi ve Metin Kaydırma için Alan Hesaplaması
    
    # Toplam yatay dolgu
    total_horizontal_padding = (FRAME_BORDER_THICKNESS * 2) + (LABEL_PADX * 2)
    # Toplam dikey dolgu
    total_vertical_padding = (FRAME_BORDER_THICKNESS * 2) + (LABEL_PADY * 2)

    # Metnin sığması gereken gerçek genişlik (kaydırma için)
    available_width = max(1, kazanc_width - total_horizontal_padding)
    # Metnin sığması gereken gerçek yükseklik (font boyutu için)
    available_height = max(1, kazanc_height - total_vertical_padding)
    
    # --- Dinamik Font Boyutu Hesaplama ---
    # İKİ SATIR metin (\n) olduğu için, yüksekliğin %80'ini değil,
    # satır başına yaklaşık %40'ını (toplam %80) hedefleyelim.
    font_size_in_pixels = int(available_height * 0.4) 
    
    # Çok küçük olmasını engelle (en az 10px)
    font_size_in_pixels = max(10, font_size_in_pixels)
    
    # Tkinter font tuple'ı için piksel cinsinden boyut (negatif sayı)
    dynamic_font_size = -font_size_in_pixels

    # --- Metin Kaydırma (Wraplength) Hesaplama ---
    wrap_length_pixels = available_width

    # 3. Altın Sarısı Çerçeve
    main_frame = tk.Frame(kazanc_window, bg=BORDER_COLOR, padx=FRAME_BORDER_THICKNESS, pady=FRAME_BORDER_THICKNESS) 
    main_frame.pack(expand=True, fill="both")
    
    # 4. Ana İçerik Alanı
    content_frame = tk.Frame(main_frame, bg=MAIN_BG_COLOR)
    content_frame.pack(expand=True, fill="both")

    # --- Sayı Formatlama ---
    def format_number(num):
        if num is None:
            return "0,00"
        try:
            # Sayıyı float'a çevir (eğer Decimal veya başka bir tipse)
            num = float(num)
            formatted = f"{num:,.2f}"
            parts = formatted.split('.')
            integer_part = parts[0].replace(',', '.')  # Binlik ayraçları nokta yap
            decimal_part = parts[1] if len(parts) > 1 else "00"
            return f"{integer_part},{decimal_part}"
        except (ValueError, TypeError):
            return "Hata"

    # Formatlanmış sayıları al
    formatted_shop_bakiye = format_number(shop_bakiye)
    formatted_sonuc = format_number(sonuc[0] if sonuc else 0.0)

    # --- Sabit Mesaj Oluşturma ---
    message_text = f"Kalan Limit: {formatted_shop_bakiye}\nNet Kazanç: {formatted_sonuc}"

    # 5. Mesaj Etiketi (Dinamik Font ve Wraplength ile)
    label = tk.Label(
        content_frame, 
        text=message_text, 
        font=("Arial", dynamic_font_size, "bold"), # GÜNCELLENDİ
        fg=TEXT_COLOR, 
        bg=MAIN_BG_COLOR, 
        padx=LABEL_PADX, 
        pady=LABEL_PADY,
        justify=tk.LEFT, # Metni sola hizala (isteğiniz buydu)
        wraplength=wrap_length_pixels # YENİ EKLENDİ
    )
    label.pack(expand=True, fill="both")

def on_app_close():
    """Uygulama kapatıldığında temizlik işlemlerini yapar."""
    global ser, app_running
    app_running = False # Seri okuma thread'ini durdur
    if ser and ser.is_open:
        ser.close() # Seri portu kapat
    root.destroy() # Tkinter penceresini yok et
    
def pc_close():
    os.system("sudo /sbin/shutdown now")

def is_serial_alive(s):
    try:
        if not s or not s.is_open:
            return False
        s.in_waiting  # Bu satır hata fırlatırsa port kopmuştur
        return True
    except:
        return False

def para_guncelle(eklenen_miktar):
    try:
        # MySQL bağlantı bilgileri
        mysql_user = 'fungames'
        mysql_password = '7396Ksn!'
        database = 'fungames'

        # Güncellenecek tablo ve sütun bilgileri
        user_table = 'w_users'
        user_column = 'balance'
        count_balance_column = 'count_balance'
        count_refunds_column = 'count_refunds'  # Yeni eklenecek sütun
        userId = 320

        # Ekstra tablo ve sütun bilgileri
        extraTable = 'w_shops'
        extraColumn = 'balance'
        extraValue = eklenen_miktar  # Eklenen miktarı al
        count_refunds_increase = eklenen_miktar * 0.1  # Eklenen miktarın %10'u

        # MySQL bağlantısı oluşturma (SSL olmadan)
        connection = mysql.connector.connect(
            user=mysql_user,
            password=mysql_password,
            database=database,
            ssl_disabled=True  # SSL olmadan bağlan
        )
        cursor = connection.cursor()
        # Shop'un bakiyesini kontrol et
        shop_bakiye_sorgu = f"SELECT {extraColumn} FROM {extraTable}"
        cursor.execute(shop_bakiye_sorgu)
        shop_bakiye = cursor.fetchone()[0]

        if shop_bakiye < eklenen_miktar:
            update_text_box("Bakiye yetersiz")
            show_notification("LİMİT YETERSİZ. LİMİTİ ARTIRIN.")
            return False
        # w_users tablosunu güncelle
        sql_query = f"UPDATE {user_table} SET {user_column} = {user_column} + {eklenen_miktar}, {count_balance_column} = {count_balance_column} + {eklenen_miktar} WHERE id = {userId}" # {count_refunds_column} = {count_refunds_column} + {count_refunds_increase}
        cursor.execute(sql_query)
        # w_shops tablosunu güncelle
        extra_sql_query = f"UPDATE {extraTable} SET {extraColumn} = {extraColumn} - {extraValue}"
        cursor.execute(extra_sql_query)
        # En yüksek statistic_id değerini al
        cursor.execute("SELECT MAX(statistic_id) FROM w_statistics_add")
        max_statistic_id = cursor.fetchone()[0]
        if max_statistic_id is None:
            max_statistic_id = 0  # Eğer tablo boşsa, ilk değeri 0 yap

        next_statistic_id = max_statistic_id + 1  # Bir sonraki değer
        # w_statistics_add tablosuna yeni veri ekleme
        add_statistics_query = f"INSERT INTO w_statistics_add (statistic_id, credit_out, money_in, user_id, shop_id) VALUES ({next_statistic_id}, {eklenen_miktar}, {eklenen_miktar}, {userId}, 1)"
        cursor.execute(add_statistics_query)
        # w_statistics tablosunu güncelleme
        update_statistics_query = f"INSERT INTO w_statistics (sum, old, user_id, shop_id, updated_at, payeer_id, `system`) VALUES ({eklenen_miktar}, 0.0000, {userId}, 1, NOW(), 294, 'handpay') ON DUPLICATE KEY UPDATE sum = sum + {eklenen_miktar}, old = 0.0000"
        cursor.execute(update_statistics_query)
        # Değişiklikleri kaydetme
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
        # Bağlantıyı kapatma
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
        # MySQL bağlantı bilgileri
        mysql_user = 'fungames'
        mysql_password = '7396Ksn!'
        database = 'fungames'

        # Kullanıcının ID'si
        userId = 320

        # MySQL bağlantısı oluşturma (SSL devre dışı)
        connection = mysql.connector.connect(
            user=mysql_user,
            password=mysql_password,
            database=database,
            ssl_disabled=True  # SSL devre dışı bırakıldı
        )
        cursor = connection.cursor()

        # Kullanıcının mevcut bakiyesini al
        select_balance_query = f"SELECT balance FROM w_users WHERE id = {userId}"
        cursor.execute(select_balance_query)
        user_balance = cursor.fetchone()[0]

        # Güncellenecek tablo ve sütun bilgileri
        user_table = 'w_users'
        user_column = 'balance'
        count_balance_column = 'count_balance'
        count_refunds_column = 'count_refunds'  # Yeni eklenecek sütun

        # Ekstra tablo ve sütun bilgileri
        extraTable = 'w_shops'
        extraColumn = 'balance'

        # w_users tablosunu güncelle (kullanıcının tüm kredisini sıfırla)
        sql_query = f"UPDATE {user_table} SET {user_column} = 0, {count_balance_column} = 0, {count_refunds_column} = 0 WHERE id = {userId}"
        cursor.execute(sql_query)

        # w_shops tablosunun balance alanına silinen miktar kadar ekle
        extra_sql_query = f"UPDATE {extraTable} SET {extraColumn} = {extraColumn} + {user_balance}"
        cursor.execute(extra_sql_query)

        # En yüksek statistic_id değerini al
        cursor.execute("SELECT IFNULL(MAX(statistic_id), 0) FROM w_statistics_add")
        max_statistic_id = cursor.fetchone()[0]
        next_statistic_id = max_statistic_id + 1  # Bir sonraki değer

        # w_statistics_add tablosuna yeni veri ekleme
        add_statistics_query = f"INSERT INTO w_statistics_add (statistic_id, credit_in, money_out, user_id, shop_id) VALUES ({next_statistic_id}, {user_balance}, {user_balance}, {userId}, 1)"
        cursor.execute(add_statistics_query)

        # w_statistics tablosunu güncelleme
        update_statistics_query = f"INSERT INTO w_statistics (sum, old, user_id, shop_id, updated_at, payeer_id, `system`, type) VALUES (-{user_balance}, 0.0000, {userId}, 1, NOW(), 294, 'handpay', 'out') ON DUPLICATE KEY UPDATE sum = sum - {user_balance}, old = 0.0000"
        cursor.execute(update_statistics_query)

        # Değişiklikleri kaydetme
        connection.commit()
        print("İşlem tamamlandı: Kullanıcının tüm kredisi sıfırlandı, w_shops tablosunun balance alanına kullanıcının mevcut bakiyesi kadar eklendi.")

    except mysql.connector.Error as error:
        print("Hata:", error)

    except ValueError as error:
        print("Hata:", error)

    finally:
        # Bağlantıyı kapatma
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
        time.sleep(2)  # Her 2 saniyede bir denetle

# --- Ana Uygulama Kurulumu ---
root = tk.Tk()
root.title("Device Communication")
root.geometry("300x400") # Başlangıç boyutunu ayarla

# Pencereyi ekranın ortasına hizala
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
x = (screen_width // 2) - (400 // 2)
y = (screen_height // 2) - (200 // 2)
root.geometry(f"+{x}+{y}")

# Metin kutusunu ortalamak için grid yapılandırması
root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(0, weight=1)

# Ortadaki metin kutusu
# Metin kutusunun yüksekliğini artırdım ki logları daha iyi görebilelim
text_box = tk.Text(root, height=5, width=30, font=("Inter", 12), bd=2, relief="solid", wrap="word")
text_box.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
update_text_box("Program başladı") # Başlangıç mesajı
text_box.config(state=tk.DISABLED) # Salt okunur yap


# Seri iletişimi başlat
port = find_arduino_port(ARDUINO_VID, ARDUINO_PID)
if port:
    try:
        ser = serial.Serial(port, 9600, timeout=1) # Baud hızını Arduino'nuzla eşleştirin
        print(f"Arduino bağlandı: {port}")
        # Seri okuma thread'ini başlat
        serial_thread = threading.Thread(target=read_serial_data, daemon=True)
        serial_thread.start()
    except serial.SerialException as e:
        print(f"Arduino'ya bağlanılamadı: {e}")
        update_text_box("Device Error")
else:
    update_text_box("Device Error")

if kurulum:
    if str(get_computer_id()) != str(id):
        print(f"ID uyuşmuyor: {get_computer_id()} != {id}")
        update_text_box("Yetkilendirme başarısız, bilgisayar kapatılıyor")
        root.after(1000, pc_close)  # 2 saniye sonra uygulamayı kapat
else:
    update_text_box("Kurulum yapılmamış, USB'den kurulum yapın.")

# Uygulama başlatıldığında bu thread'i başlat
arduino_thread = threading.Thread(target=arduino_monitor, daemon=True)
arduino_thread.start()


# Seri kuyruğunu periyodik olarak kontrol etmeye başla
root.after(10, check_serial_queue)
root.after(3000, check_balance_for_game)
root.after(2000, close)
# Pencere kapatma protokolünü ayarla
root.protocol("WM_DELETE_WINDOW", on_app_close)

# Ana döngüyü başlat
root.mainloop()