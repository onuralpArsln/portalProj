#!/usr/bin/env python3
"""
Mock Arduino Script (socat versiyonu) - Sanal Arduino Simülatörü

Bu script, kumanda.py'yi gerçek bir Arduino bağlı olduğuna inandırmak için
socat aracını kullanarak sanal seri port çifti oluşturur.

KURULUM:
    sudo apt install socat

KULLANIM:
1. Bu scripti çalıştırın: python3 mock_arduino_socat.py
2. Script otomatik olarak /tmp/ttyVirtual0 ve /tmp/ttyVirtual1 oluşturur
3. kumanda.py'yi değiştirilmiş haliyle çalıştırın (kumanda_test.py)

KOMUTLAR (terminalde):
- 'auth' / 'a': Yetkilendirme ID'si gönder
- 'sil' / 's': Sil komutu (3217)
- 'yukle5' / 'y5': 5 TL yükle
- 'yukle10' / 'y10': 10 TL yükle
- ... (diğer yükle komutları)
- 'oyun' / 'o': Oyun aç/kapat
- 'kazanc' / 'k': Kazanç göster
- 'quit' / 'q': Çıkış
"""

import os
import subprocess
import threading
import time
import sys
import serial

# Sanal port yolları
VIRTUAL_PORT_ARDUINO = "/tmp/ttyVirtual0"  # Mock Arduino bu portu kullanır
VIRTUAL_PORT_KUMANDA = "/tmp/ttyVirtual1"  # kumanda.py bu portu kullanır

BAUD_RATE = 9600

# Yetkilendirme ID'si
AUTH_ID = None


def check_socat():
    """socat'ın kurulu olup olmadığını kontrol eder."""
    try:
        subprocess.run(["which", "socat"], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False


def load_auth_id():
    """open_id.txt dosyasından şifreli ID'yi okur ve çözer."""
    global AUTH_ID
    try:
        from cryptography.fernet import Fernet
        KEY_B64 = b"o3QqhjSBDaIEhd8h_e8icgou0socOWYTG9S_eFIALo0="
        F = Fernet(KEY_B64)
        
        with open("open_id.txt", "r") as f:
            content = f.read()
            AUTH_ID = F.decrypt(content.encode()).decode("utf-8")
            print(f"[INFO] Yetkilendirme ID'si yüklendi: {AUTH_ID[:8]}...")
    except FileNotFoundError:
        print("[UYARI] open_id.txt bulunamadı.")
        # Bilgisayar ID'sini hesapla
        AUTH_ID = get_computer_id()
        print(f"[INFO] Bilgisayar ID kullanılıyor: {AUTH_ID}")
    except Exception as e:
        print(f"[HATA] ID okuma hatası: {e}")
        AUTH_ID = get_computer_id()


def get_computer_id():
    """Bilgisayarın benzersiz ID'sini hesaplar (kumanda.py ile aynı)."""
    import hashlib
    try:
        result = subprocess.check_output("wmic csproduct get uuid", shell=True).decode()
        uuid = result.split("\n")[1].strip()
    except:
        result = subprocess.check_output("cat /etc/machine-id", shell=True).decode()
        uuid = result.strip()
    return hashlib.sha256(uuid.encode()).hexdigest()[:14]


class MockArduinoSocat:
    def __init__(self):
        self.socat_process = None
        self.serial_port = None
        self.running = False
        self.read_thread = None

    def start_socat(self):
        """socat ile sanal seri port çifti oluşturur."""
        # Eski portları temizle
        for port in [VIRTUAL_PORT_ARDUINO, VIRTUAL_PORT_KUMANDA]:
            if os.path.exists(port):
                os.remove(port)
        
        # socat komutu
        cmd = [
            "socat",
            "-d", "-d",
            f"pty,raw,echo=0,link={VIRTUAL_PORT_ARDUINO}",
            f"pty,raw,echo=0,link={VIRTUAL_PORT_KUMANDA}"
        ]
        
        print(f"[INFO] socat başlatılıyor...")
        self.socat_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # socat'ın portları oluşturması için bekle
        time.sleep(1)
        
        if not os.path.exists(VIRTUAL_PORT_ARDUINO):
            raise RuntimeError("Sanal portlar oluşturulamadı!")
        
        print(f"[OK] Sanal portlar oluşturuldu:")
        print(f"     Arduino tarafı: {VIRTUAL_PORT_ARDUINO}")
        print(f"     Kumanda tarafı: {VIRTUAL_PORT_KUMANDA}")

    def connect_serial(self):
        """Arduino tarafındaki sanal porta bağlanır."""
        try:
            self.serial_port = serial.Serial(
                VIRTUAL_PORT_ARDUINO,
                BAUD_RATE,
                timeout=0.1
            )
            print(f"[OK] Seri port bağlantısı kuruldu")
            return True
        except serial.SerialException as e:
            print(f"[HATA] Seri port bağlantı hatası: {e}")
            return False

    def send_data(self, data):
        """Arduino'dan veri gönderir (kumanda.py'ye)."""
        if self.serial_port and self.serial_port.is_open:
            message = f"{data}\n"
            self.serial_port.write(message.encode('utf-8'))
            self.serial_port.flush()
            print(f"[GÖNDER] -> {data}")
        else:
            print("[HATA] Seri port bağlı değil!")

    def read_data(self):
        """kumanda.py'den gelen verileri okur."""
        while self.running:
            if self.serial_port and self.serial_port.is_open:
                try:
                    if self.serial_port.in_waiting > 0:
                        data = self.serial_port.readline().decode('utf-8').strip()
                        if data:
                            print(f"[ALINDI] <- {data}")
                except Exception as e:
                    if self.running:
                        print(f"[HATA] Okuma hatası: {e}")
            time.sleep(0.01)

    def start(self):
        """Mock Arduino'yu başlatır."""
        if not check_socat():
            print("[HATA] socat kurulu değil!")
            print("       Kurmak için: sudo apt install socat")
            sys.exit(1)
        
        self.start_socat()
        
        if not self.connect_serial():
            self.stop()
            sys.exit(1)
        
        self.running = True
        
        # Okuma thread'ini başlat
        self.read_thread = threading.Thread(target=self.read_data, daemon=True)
        self.read_thread.start()
        
        load_auth_id()
        
        print(f"\n{'='*60}")
        print("[MOCK ARDUINO HAZIR]")
        print(f"{'='*60}")
        print(f"\nkumanda.py'yi test etmek için şunları yapın:")
        print(f"")
        print(f"1. kumanda.py'nin bir kopyasını oluşturun (veya doğrudan değiştirin)")
        print(f"2. find_arduino_port fonksiyonunu şu şekilde değiştirin:")
        print(f"")
        print(f"   def find_arduino_port(vid_list, pid_list):")
        print(f"       return '{VIRTUAL_PORT_KUMANDA}'")
        print(f"")
        print(f"3. veya kumanda_test.py dosyasını çalıştırın")
        print(f"{'='*60}")
        
        self.print_commands()

    def print_commands(self):
        """Kullanılabilir komutları yazdırır."""
        print("\n[KOMUTLAR]")
        print("-" * 40)
        print("  auth, a      : Yetkilendirme ID'si gönder")
        print("  sil, s       : Sil komutu (3217)")
        print("  yukle5, y5   : 5 TL yükle")
        print("  yukle10, y10 : 10 TL yükle")
        print("  yukle20, y20 : 20 TL yükle")
        print("  yukle50, y50 : 50 TL yükle")
        print("  yukle100     : 100 TL yükle")
        print("  yukle1, y1   : 1 TL yükle")
        print("  yukle500     : 500 TL yükle")
        print("  oyun, o      : Oyun aç/kapat (3357)")
        print("  kazanc, k    : Kazanç göster (4455)")
        print("  custom <val> : Özel değer gönder")
        print("  help, h      : Yardım")
        print("  quit, q      : Çıkış")
        print("-" * 40)

    def stop(self):
        """Mock Arduino'yu durdurur."""
        self.running = False
        
        if self.serial_port:
            self.serial_port.close()
        
        if self.socat_process:
            self.socat_process.terminate()
            self.socat_process.wait()
        
        # Sanal portları temizle
        for port in [VIRTUAL_PORT_ARDUINO, VIRTUAL_PORT_KUMANDA]:
            if os.path.exists(port):
                try:
                    os.remove(port)
                except:
                    pass
        
        print("\n[INFO] Mock Arduino kapatıldı.")

    def process_command(self, cmd):
        """Terminal komutlarını işler."""
        cmd = cmd.strip().lower()
        
        if cmd in ['auth', 'a']:
            if AUTH_ID:
                self.send_data(AUTH_ID)
            else:
                print("[HATA] Yetkilendirme ID'si yüklenemedi!")
                
        elif cmd in ['sil', 's']:
            self.send_data("3217")
            
        elif cmd in ['yukle5', 'y5']:
            # value=1 -> 1*5=5 TL, format: 31<value>7
            self.send_data("3117")
            
        elif cmd in ['yukle10', 'y10']:
            # value=2 -> 2*5=10 TL
            self.send_data("3127")
            
        elif cmd in ['yukle20', 'y20']:
            # value=4 -> 4*5=20 TL
            self.send_data("3147")
            
        elif cmd in ['yukle50', 'y50']:
            # value=10 -> 10*5=50 TL
            self.send_data("31107")
            
        elif cmd in ['yukle100', 'y100']:
            self.send_data("3567")
            
        elif cmd in ['yukle1', 'y1']:
            self.send_data("3131")
            
        elif cmd in ['yukle500', 'y500']:
            self.send_data("3687")
            
        elif cmd in ['oyun', 'o']:
            self.send_data("3357")
            
        elif cmd in ['kazanc', 'k']:
            self.send_data("4455")
            
        elif cmd.startswith('custom '):
            custom_val = cmd.split(' ', 1)[1]
            self.send_data(custom_val)
            
        elif cmd in ['quit', 'q']:
            return False
            
        elif cmd in ['help', 'h', '?']:
            self.print_commands()
            
        elif cmd:
            print(f"[UYARI] Bilinmeyen komut: '{cmd}'. 'help' yazın.")
            
        return True


def main():
    arduino = MockArduinoSocat()
    
    try:
        arduino.start()
        
        # Otomatik yetkilendirme
        print("\n[INFO] 2 saniye sonra otomatik yetkilendirme gönderilecek...")
        time.sleep(2)
        arduino.process_command('auth')
        
        # Komut döngüsü
        while True:
            try:
                cmd = input("\n[KOMUT]> ").strip()
                if not arduino.process_command(cmd):
                    break
            except EOFError:
                break
                
    except KeyboardInterrupt:
        print("\n\n[INFO] Ctrl+C ile çıkılıyor...")
    finally:
        arduino.stop()


if __name__ == "__main__":
    main()
