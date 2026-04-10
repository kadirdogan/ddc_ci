# CH552 DDC/CI Pot Controller

Analog potansiyometre ile monitör parlaklık ve kontrast kontrolü.  
CH552 mikrodenetleyici → USB HID → Python daemon → DDC/CI (Windows dxva2)

---

## Donanım

| Bileşen | Detay |
|---|---|
| MCU | WeAct Studio CH552 Core Board (DIP20) |
| POT1 (Brightness) | 10kΩ — orta bacak P1.1, uçlar GND / 3.3V |
| POT2 (Contrast) | 10kΩ — orta bacak P1.4, uçlar GND / 3.3V |
| LED | P3.0 — enumerate göstergesi |

---

## Proje Yapısı

```
ddc_ci/
├── monitor_ctrl.py          ← Ana Python daemon
├── CHANGELOG.txt
└── firmware/                ← CH552 firmware
    ├── ch552_pot_hid.ino
    └── src/
        ├── USBconstant.c/h  ← Vendor HID descriptor (0xFF00)
        ├── USBhandler.c/h   ← USB interrupt handler
        ├── USBHIDKeyboard.c/h ← EP1 send, UpPoint1_Busy
        └── include/
            ├── ch5xx.h
            ├── ch5xx_datatypes.h
            └── ch5xx_usb.h
```

---

## Firmware

### Arduino IDE Ayarları

- **Board:** CH552 Board
- **Clock:** 24 MHz (internal)
- **USB Settings:** USER CODE w/ 148B USB ram

### USB Cihaz

```
VID: 0x1209   PID: 0xC55D
Usage Page: 0xFF00 (Vendor Defined)
```

Windows bu cihazı klavye olarak görmez, sürücü kurulumu gerekmez.

### ADC

CH552 ADC 8-bit, dahili referans nedeniyle gerçek aralık **4–174**.  
Kanal seçimi `ADC_CHAN0` / `ADC_CHAN1` bitleri ile yapılıyor.

```
P1.1 → ADC kanal 0 (CHAN1=0, CHAN0=0)
P1.4 → ADC kanal 1 (CHAN1=0, CHAN0=1)
```

### HID Paketi

```
HIDKey[0] = brightness (ADC kanal 0)
HIDKey[1] = contrast   (ADC kanal 1)
```

### Flash

BOOT moduna girmek için: P3.6 butonuna basılı tut → USB tak → bırak.  
WCHISPTool v3.9 ile flash yap.

---

## Python Daemon

### Bağımlılıklar

```
pip install hid
```

### Çalıştırma

```
python monitor_ctrl.py
```

### Mimari

- **HID okuma:** `dev.read(64)` non-blocking, 20ms poll
- **DDC/CI:** `dxva2.SetMonitorBrightness` / `SetMonitorContrast` — Windows native API
- **Queue:** `maxsize=1` — eski komut işlenmeden yeni gelirse eski atılır
- **OSD:** Win32 GDI layered window, sağ alt köşe, Sony PVM fosfor yeşil, 2 sn auto-hide
- **Reconnect:** USB çekilince `signal lost` mesajı, otomatik yeniden bağlanma

### Değer Dönüşümü

```python
ADC_MIN = 4
ADC_MAX = 174

def map_val(raw):
    val = (ADC_MAX - raw) * 100 // (ADC_MAX - ADC_MIN)
    return max(0, min(100, val))
```

Pot tam sola → 100, tam sağa → 0 (ters bağlantı nedeniyle).

---

## Bilinen Sınırlamalar

- OSD exclusive fullscreen (DirectX/Vulkan) üzerinde görünmez
- Contrast yanıtı brightness'a göre daha kaba — Dell SE2717H monitörün DDC/CI implementasyonu

---

## Sonraki Adımlar

- Firmware smoothing buffer (ADC gürültüsünü azalt)
- Standalone exe (PyInstaller)
- Özel PCB tasarımı

---

## Kaynak

Blog yazısı: [DDC/CI: CH552 ve Python ile Monitör Kontrolü](https://doankadir.blogspot.com)  
Kaynak kod: [github.com/kadirdogan/ddc_ci](https://github.com/kadirdogan/ddc_ci)
