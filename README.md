# CH552 DDC/CI Pot Controller

> 🌐 [Türkçe](README.tr.md)

Monitor brightness and contrast control via analog potentiometers.  
CH552 microcontroller → USB HID → Python daemon → DDC/CI (Windows dxva2)

---

## Hardware

| Component | Detail |
|---|---|
| MCU | WeAct Studio CH552 Core Board (DIP20) |
| POT1 (Brightness) | 10kΩ — wiper to P1.1, ends to GND / 3.3V |
| POT2 (Contrast) | 10kΩ — wiper to P1.4, ends to GND / 3.3V |
| LED | P3.0 — enumeration indicator |

---

## Project Structure

```
ddc_ci/
├── monitor_ctrl.py          ← Main Python daemon
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

### Arduino IDE Settings

- **Board:** CH552 Board
- **Clock:** 24 MHz (internal)
- **USB Settings:** USER CODE w/ 148B USB ram

### USB Device

```
VID: 0x1209   PID: 0xC55D
Usage Page: 0xFF00 (Vendor Defined)
```

Windows does not enumerate this as a keyboard; no driver installation required.

### ADC

The CH552 ADC is 8-bit. Due to the internal reference, the effective range is **4–174**.  
Channel selection is done via `ADC_CHAN0` / `ADC_CHAN1` bits.

```
P1.1 → ADC channel 0 (CHAN1=0, CHAN0=0)
P1.4 → ADC channel 1 (CHAN1=0, CHAN0=1)
```

### HID Packet

```
HIDKey[0] = brightness (ADC channel 0)
HIDKey[1] = contrast   (ADC channel 1)
```

### Flashing

To enter BOOT mode: hold P3.6 button → plug USB → release.  
Flash using WCHISPTool v3.9.

---

## Python Daemon

### Dependencies

```
pip install hid
```

### Running

```
python monitor_ctrl.py
```

### Architecture

- **HID read:** `dev.read(64)` non-blocking, 20ms poll
- **DDC/CI:** `dxva2.SetMonitorBrightness` / `SetMonitorContrast` — Windows native API
- **Queue:** `maxsize=1` — new value drops the previous if unprocessed
- **OSD:** Win32 GDI layered window, bottom-right corner, Sony PVM phosphor green, 2s auto-hide
- **Reconnect:** prints `signal lost` on USB disconnect, reconnects automatically

### Value Mapping

```python
ADC_MIN = 4
ADC_MAX = 174

def map_val(raw):
    val = (ADC_MAX - raw) * 100 // (ADC_MAX - ADC_MIN)
    return max(0, min(100, val))
```

Pot fully left → 100, fully right → 0 (due to reverse wiring).

### Contrast Floor

Brightness maps to `[0, 100]`; contrast maps to `[25, 100]`:

```python
CONTRAST_MIN = 25
CONTRAST_MAX = 100

def map_contrast(raw):
    val = (ADC_MAX - raw) * (CONTRAST_MAX - CONTRAST_MIN) // (ADC_MAX - ADC_MIN) + CONTRAST_MIN
    return max(CONTRAST_MIN, min(CONTRAST_MAX, val))
```

The monitor's own OSD menu can go down to 0, but this tool bottoms out at 25. Third-party tools like Screenbright may have their own floors (e.g. 20). To change the limit, edit the `CONTRAST_MIN` constant.

---

## Known Limitations

- OSD may not appear in true exclusive fullscreen (`VK_EXT_full_screen_exclusive`) mode
- Contrast response is coarser than brightness — limitation of the Dell SE2717H DDC/CI implementation

---

## Roadmap

- ADC noise: partially addressed with hysteresis; RC filter + oversampling deferred
- **Input source switching via DDC/CI** — confirmed working; VGA=`0x01`, HDMI-1=`0x11` (VCP 0x60); add a button or third pot position to toggle inputs
- Standalone exe (PyInstaller)
- Custom PCB design

---

## References

Blog post: [DDC/CI: Monitor Control with CH552 and Python](https://doankadir.blogspot.com)  
Source code: [github.com/kadirdogan/ddc_ci](https://github.com/kadirdogan/ddc_ci)
