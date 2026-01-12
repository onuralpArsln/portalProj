# Kumanda Master System

Captive portal ile kontrol edilen Arduino simülatörü ve kumanda sistemi.

## Gereksinimler

- Linux (Pop!_OS, Ubuntu, Debian)
- Python 3.10+
- WiFi kartı (hostapd destekli)

## Kurulum

```bash
sudo ./install.sh
```

## Kullanım

```bash
./start.sh
```

veya manuel olarak:

```bash
xhost +local:root
sudo python3 master.py
```

## WiFi Ayarları

WiFi arayüzünüz farklıysa `hostapd.conf` ve `master.py` dosyalarında `INTERFACE` değişkenini güncelleyin.

Varsayılan: `wlp5s0`

WiFi arayüzünüzü bulmak için:
```bash
ip link show
```

## Portal Butonları

| Buton | Kod | İşlev |
|-------|-----|-------|
| 5 TL | 3117 | 5 TL yükle |
| 10 TL | 3127 | 10 TL yükle |
| 20 TL | 3147 | 20 TL yükle |
| 50 TL | 31107 | 50 TL yükle |
| 100 TL | 3567 | 100 TL yükle |
| Sil | 3217 | Bakiye sil |
| Oyun | 3357 | Oyun aç/kapat |
| Kazanç | 4455 | Kazanç göster |

## Dosyalar

- `master.py` - Ana kontrol scripti
- `portal.html` - Captive portal sayfası
- `kumanda.py` - Kumanda uygulaması
- `hostapd.conf` - WiFi AP ayarları
- `dnsmasq.conf` - DHCP/DNS ayarları
- `install.sh` - Kurulum scripti
- `start.sh` - Başlatma scripti
