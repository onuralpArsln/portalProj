#!/usr/bin/env python3
"""
Mock Arduino Script - Sanal Arduino Simülatörü

Bu script, kumanda.py'yi gerçek bir Arduino bağlı olduğuna inandırmak için
sanal bir seri port oluşturur. socat aracını kullanarak sanal seri port çifti
oluşturur ve kumanda.py'nin beklediği komutları gönderir.

Kullanım:
1. Bu scripti çalıştırın: python3 mock_arduino.py
2. Terminalde gösterilen sanal port yolunu not edin
3. kumanda.py'deki find_arduino_port fonksiyonunu geçici olarak bu portu
   döndürecek şekilde değiştirin veya sanal portu kullanın

Komutlar (terminal'den girin):
- 'auth' veya 'a': Yetkilendirme ID'si gönder
- 'sil' veya 's': Sil komutu (3217) gönder
- 'yukle5' veya 'y5': 5 TL yükle (3117)
- 'yukle10' veya 'y10': 10 TL yükle (3127)
- 'yukle20' veya 'y20': 20 TL yükle (3147)
- 'yukle50' veya 'y50': 50 TL yükle (31107)
- 'yukle100' veya 'y100': 100 TL yükle (3567)
- 'yukle1' veya 'y1': 1 TL yükle (3131)
- 'yukle500' veya 'y500': 500 TL yükle (3687)
- 'oyun' veya 'o': Oyun aç/kapat (3357)
- 'kazanc' veya 'k': Kazanç göster (4455)
- 'quit' veya 'q': Çıkış
"""

import os
import pty
import subprocess
import threading
import time
import sys
import select

# Sanal port ayarları
BAUD_RATE = 9600

# Yetkilendirme ID'si - kumanda.py'deki open_id.txt dosyasından okunmalı
# Bu değeri kumanda.py'deki ID ile eşleştirmeniz gerekir
AUTH_ID = None

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
        print("[UYARI] open_id.txt bulunamadı. 'auth' komutu çalışmayacak.")
        AUTH_ID = "test_auth_id_12345"  # Test için varsayılan
    except Exception as e:
        print(f"[HATA] ID okuma hatası: {e}")
        AUTH_ID = "test_auth_id_12345"

class MockArduino:
    def __init__(self):
        self.master_fd = None
        self.slave_fd = None
        self.slave_path = None
        self.running = False
        
    def create_virtual_serial(self):
        """PTY kullanarak sanal seri port oluşturur."""
        self.master_fd, self.slave_fd = pty.openpty()
        self.slave_path = os.ttyname(self.slave_fd)
        print(f"\n{'='*60}")
        print(f"[SANAL ARDUİNO BAŞLATILDI]")
        print(f"{'='*60}")
        print(f"Sanal Port: {self.slave_path}")
        print(f"\nkumanda.py'yi bu portla test etmek için:")
        print(f"1. kumanda.py'de find_arduino_port fonksiyonunu şu şekilde değiştirin:")
        print(f"   return '{self.slave_path}'")
        print(f"   (veya VID/PID kontrolünü geçici olarak devre dışı bırakın)")
        print(f"{'='*60}\n")
        return self.slave_path

    def send_data(self, data):
        """Arduino'dan veri gönderir (kumanda.py'ye)."""
        if self.master_fd:
            message = f"{data}\n"
            os.write(self.master_fd, message.encode('utf-8'))
            print(f"[GÖNDER] -> {data}")
        else:
            print("[HATA] Sanal port oluşturulmamış!")

    def read_data(self):
        """kumanda.py'den gelen verileri okur."""
        while self.running:
            if self.master_fd:
                try:
                    ready, _, _ = select.select([self.master_fd], [], [], 0.1)
                    if ready:
                        data = os.read(self.master_fd, 1024).decode('utf-8').strip()
                        if data:
                            print(f"[ALINDI] <- {data}")
                except Exception as e:
                    if self.running:
                        print(f"[HATA] Okuma hatası: {e}")
            time.sleep(0.01)

    def start(self):
        """Mock Arduino'yu başlatır."""
        self.running = True
        self.create_virtual_serial()
        
        # Okuma thread'ini başlat
        read_thread = threading.Thread(target=self.read_data, daemon=True)
        read_thread.start()
        
        load_auth_id()
        
        print("\n[KOMUTLAR]")
        print("-" * 40)
        print("  auth, a     : Yetkilendirme ID'si gönder")
        print("  sil, s      : Sil komutu (3217)")
        print("  yukle5, y5  : 5 TL yükle")
        print("  yukle10, y10: 10 TL yükle")
        print("  yukle20, y20: 20 TL yükle")
        print("  yukle50, y50: 50 TL yükle")
        print("  yukle100, y100: 100 TL yükle")
        print("  yukle1, y1  : 1 TL yükle")
        print("  yukle500, y500: 500 TL yükle")
        print("  oyun, o     : Oyun aç/kapat")
        print("  kazanc, k   : Kazanç göster")
        print("  custom <val>: Özel değer gönder")
        print("  quit, q     : Çıkış")
        print("-" * 40)
        print()

    def stop(self):
        """Mock Arduino'yu durdurur."""
        self.running = False
        if self.master_fd:
            os.close(self.master_fd)
        if self.slave_fd:
            os.close(self.slave_fd)
        print("\n[INFO] Mock Arduino kapatıldı.")

    def process_command(self, cmd):
        """Terminal komutlarını işler ve ilgili Arduino çıkışını gönderir."""
        cmd = cmd.strip().lower()
        
        if cmd in ['auth', 'a']:
            if AUTH_ID:
                self.send_data(AUTH_ID)
            else:
                print("[HATA] Yetkilendirme ID'si yüklenmedi!")
                
        elif cmd in ['sil', 's']:
            self.send_data("3217")
            
        elif cmd in ['yukle5', 'y5']:
            # 5 TL = value * 5 = 1, yani 3 + 1 + 1 + 7 = 3117
            self.send_data("3117")
            
        elif cmd in ['yukle10', 'y10']:
            # 10 TL = value * 5 = 2, yani 3 + 1 + 2 + 7 = 3127
            self.send_data("3127")
            
        elif cmd in ['yukle20', 'y20']:
            # 20 TL = value * 5 = 4, yani 3 + 1 + 4 + 7 = 3147
            self.send_data("3147")
            
        elif cmd in ['yukle50', 'y50']:
            # 50 TL = value * 5 = 10, yani 3 + 1 + 10 + 7 = 31107
            self.send_data("31107")
            
        elif cmd in ['yukle100', 'y100']:
            # 100 TL direkt kod
            self.send_data("3567")
            
        elif cmd in ['yukle1', 'y1']:
            # 1 TL direkt kod  
            self.send_data("3131")
            
        elif cmd in ['yukle500', 'y500']:
            # 500 TL direkt kod
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
            print("\n[KOMUTLAR]")
            print("  auth, a: Yetkilendirme ID'si gönder")
            print("  sil, s: Sil komutu")
            print("  yukle<N>, y<N>: N TL yükle (1,5,10,20,50,100,500)")
            print("  oyun, o: Oyun aç/kapat")
            print("  kazanc, k: Kazanç göster")
            print("  custom <val>: Özel değer gönder")
            print("  quit, q: Çıkış\n")
            
        elif cmd:
            print(f"[UYARI] Bilinmeyen komut: {cmd}. 'help' yazın.")
            
        return True


def main():
    arduino = MockArduino()
    
    try:
        arduino.start()
        
        # Önce otomatik olarak yetkilendirme gönder
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
