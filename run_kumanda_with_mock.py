#!/usr/bin/env python3
"""
run_kumanda_with_mock.py - kumanda.py'yi sanal Arduino ile çalıştırır

Bu script, kumanda.py'yi DEĞİŞTİRMEDEN sanal seri port ile çalıştırır.
Serial port tarama fonksiyonunu çalışma zamanında yamalayarak
sanal porta bağlanmasını sağlar.

KULLANIM:
1. Terminal 1: python3 mock_arduino_socat.py
2. Terminal 2: python3 run_kumanda_with_mock.py

Bu script:
- serial.tools.list_ports.comports() fonksiyonunu yamalayarak
  sanal portu gerçek bir Arduino gibi gösterir
- kumanda.py'yi olduğu gibi çalıştırır
"""

import sys
import os
from collections import namedtuple

# Sanal port ayarları
VIRTUAL_PORT = "/tmp/ttyVirtual1"

# Sahte Arduino VID/PID (kumanda.py'de tanımlı olanlarla eşleşmeli)
FAKE_VID = 0x1A86  # CH340 VID
FAKE_PID = 0x7523  # CH340 PID


def check_virtual_port():
    """Sanal portun var olup olmadığını kontrol eder."""
    if not os.path.exists(VIRTUAL_PORT):
        print("=" * 60)
        print("HATA: Sanal port bulunamadı!")
        print(f"       {VIRTUAL_PORT} mevcut değil.")
        print()
        print("ÇÖZÜM: Önce mock Arduino'yu başlatın:")
        print("       python3 mock_arduino_socat.py")
        print("=" * 60)
        sys.exit(1)


def patch_serial_ports():
    """
    serial.tools.list_ports.comports() fonksiyonunu yamar.
    Sanal portu gerçek bir Arduino cihazı gibi gösterir.
    """
    import serial.tools.list_ports as list_ports
    
    # Orijinal fonksiyonu sakla
    original_comports = list_ports.comports
    
    # Sahte port bilgisi için namedtuple oluştur
    # pyserial'ın ListPortInfo sınıfına benzer yapı
    FakePortInfo = namedtuple('FakePortInfo', [
        'device', 'name', 'description', 'hwid',
        'vid', 'pid', 'serial_number', 'location',
        'manufacturer', 'product', 'interface'
    ])
    
    def patched_comports(include_links=False):
        """Yamalı comports - sanal portu da içerir."""
        # Önce gerçek portları al
        real_ports = list(original_comports(include_links))
        
        # Sanal port var mı kontrol et
        if os.path.exists(VIRTUAL_PORT):
            # Sahte Arduino port bilgisi oluştur
            fake_port = FakePortInfo(
                device=VIRTUAL_PORT,
                name=os.path.basename(VIRTUAL_PORT),
                description="Mock Arduino (CH340)",
                hwid=f"USB VID:PID={FAKE_VID:04X}:{FAKE_PID:04X}",
                vid=FAKE_VID,
                pid=FAKE_PID,
                serial_number="MOCK12345",
                location=None,
                manufacturer="Mock",
                product="Mock Arduino Uno",
                interface=None
            )
            
            # Sahte portu listeye ekle
            real_ports.insert(0, fake_port)  # En başa ekle
            print(f"[MOCK] Sanal Arduino eklendi: {VIRTUAL_PORT}")
        
        return real_ports
    
    # Fonksiyonu değiştir
    list_ports.comports = patched_comports
    print("[MOCK] serial.tools.list_ports.comports yamalendi.")


def main():
    print("=" * 60)
    print("KUMANDA.PY - MOCK ARDUINO MODU")
    print("=" * 60)
    print()
    
    # Sanal portun varlığını kontrol et
    check_virtual_port()
    print(f"[OK] Sanal port bulundu: {VIRTUAL_PORT}")
    
    # Serial port taramasını yamala
    patch_serial_ports()
    
    print()
    print("[*] kumanda.py başlatılıyor...")
    print("=" * 60)
    print()
    
    # kumanda.py'yi çalıştır
    # exec() ile aynı işlem içinde çalıştırıyoruz
    kumanda_path = os.path.join(os.path.dirname(__file__), "kumanda.py")
    
    if not os.path.exists(kumanda_path):
        print(f"HATA: kumanda.py bulunamadı: {kumanda_path}")
        sys.exit(1)
    
    # kumanda.py'yi bu script'in ortamında çalıştır
    with open(kumanda_path, 'r', encoding='utf-8') as f:
        code = f.read()
    
    # __name__ ve __file__ ayarla
    exec_globals = {
        '__name__': '__main__',
        '__file__': kumanda_path,
    }
    
    exec(compile(code, kumanda_path, 'exec'), exec_globals)


if __name__ == "__main__":
    main()
