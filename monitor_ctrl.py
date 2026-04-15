import hid
import threading
import queue
import time
import ctypes
import ctypes.wintypes as wintypes
from ctypes import windll, byref, sizeof

user32   = windll.user32
gdi32    = windll.gdi32
kernel32 = windll.kernel32
dxva2    = windll.dxva2

try:
    import psutil
    psutil.Process().nice(psutil.HIGH_PRIORITY_CLASS)
except Exception:
    pass

user32.CreateWindowExW.restype  = wintypes.HWND
user32.CreateWindowExW.argtypes = [
    wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR,
    wintypes.DWORD, ctypes.c_int, ctypes.c_int,
    ctypes.c_int, ctypes.c_int,
    wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID
]
user32.DefWindowProcW.restype  = ctypes.c_longlong
user32.DefWindowProcW.argtypes = [
    wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
]
user32.RegisterClassExW.restype  = ctypes.c_ushort
user32.SetLayeredWindowAttributes.restype  = wintypes.BOOL
user32.SetLayeredWindowAttributes.argtypes = [
    wintypes.HWND, wintypes.COLORREF, ctypes.c_byte, wintypes.DWORD
]

WNDPROCTYPE = ctypes.WINFUNCTYPE(
    ctypes.c_longlong,
    wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
)

class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize",        wintypes.UINT),
        ("style",         wintypes.UINT),
        ("lpfnWndProc",   WNDPROCTYPE),
        ("cbClsExtra",    ctypes.c_int),
        ("cbWndExtra",    ctypes.c_int),
        ("hInstance",     wintypes.HINSTANCE),
        ("hIcon",         wintypes.HICON),
        ("hCursor",       wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName",  wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
        ("hIconSm",       wintypes.HICON),
    ]

class PAINTSTRUCT(ctypes.Structure):
    _fields_ = [
        ("hdc",         wintypes.HDC),
        ("fErase",      wintypes.BOOL),
        ("rcPaint",     wintypes.RECT),
        ("fRestore",    wintypes.BOOL),
        ("fIncUpdate",  wintypes.BOOL),
        ("rgbReserved", ctypes.c_byte * 32),
    ]

class LOGFONTW(ctypes.Structure):
    _fields_ = [
        ("lfHeight",         ctypes.c_long),
        ("lfWidth",          ctypes.c_long),
        ("lfEscapement",     ctypes.c_long),
        ("lfOrientation",    ctypes.c_long),
        ("lfWeight",         ctypes.c_long),
        ("lfItalic",         ctypes.c_byte),
        ("lfUnderline",      ctypes.c_byte),
        ("lfStrikeOut",      ctypes.c_byte),
        ("lfCharSet",        ctypes.c_byte),
        ("lfOutPrecision",   ctypes.c_byte),
        ("lfClipPrecision",  ctypes.c_byte),
        ("lfQuality",        ctypes.c_byte),
        ("lfPitchAndFamily", ctypes.c_byte),
        ("lfFaceName",       ctypes.c_wchar * 32),
    ]

class PHYSICAL_MONITOR(ctypes.Structure):
    _fields_ = [
        ("hPhysicalMonitor", wintypes.HANDLE),
        ("szPhysicalMonitorDescription", ctypes.c_wchar * 128)
    ]

WS_POPUP         = 0x80000000
WS_EX_LAYERED    = 0x00080000
WS_EX_TRANSPARENT= 0x00000020
WS_EX_TOPMOST    = 0x00000008
WS_EX_NOACTIVATE = 0x08000000
WS_EX_ALL        = WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST | WS_EX_NOACTIVATE
LWA_ALPHA        = 0x00000002
LWA_COLORKEY     = 0x00000001
COLOR_BG         = 0x001a1a1a
COLOR_GREEN      = 0x0033ff33
CHROMA_KEY       = 0x00ff00ff
CLASS_NAME       = "PVM_OSD_V3"

VENDOR_ID  = 0x1209
PRODUCT_ID = 0xC55D

ADC_MIN = 4
ADC_MAX = 174

CONTRAST_MIN = 25
CONTRAST_MAX = 100

THROTTLE_MS = 80  # min DDC komutları arası süre (ms); ilk değişiklik anında gönderilir

def map_brightness(raw):
    val = (ADC_MAX - raw) * 100 // (ADC_MAX - ADC_MIN)
    return max(0, min(100, val))

def map_contrast(raw):
    val = (ADC_MAX - raw) * (CONTRAST_MAX - CONTRAST_MIN) // (ADC_MAX - ADC_MIN) + CONTRAST_MIN
    return max(CONTRAST_MIN, min(CONTRAST_MAX, val))

# ── dxva2 monitor handle'lari ────────────────────────────
_monitor_handles = []

def _get_monitor_handles():
    global _monitor_handles
    handles = []
    MonitorEnumProc = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HMONITOR, wintypes.HDC,
        ctypes.POINTER(wintypes.RECT), wintypes.LPARAM
    )
    def _cb(hMon, hDC, lpRect, dwData):
        count = wintypes.DWORD(0)
        dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR(hMon, byref(count))
        phys = (PHYSICAL_MONITOR * count.value)()
        dxva2.GetPhysicalMonitorsFromHMONITOR(hMon, count.value, phys)
        for m in phys:
            handles.append(m.hPhysicalMonitor)
        return True
    user32.EnumDisplayMonitors(None, None, MonitorEnumProc(_cb), 0)
    _monitor_handles = handles

# ── DDC/CI queue worker ──────────────────────────────────
_ddc_queue = queue.Queue(maxsize=1)

def _ddc_worker():
    _get_monitor_handles()
    while True:
        try:
            brightness, contrast = _ddc_queue.get()
            for h in _monitor_handles:
                if brightness is not None:
                    dxva2.SetMonitorBrightness(h, brightness)
                if contrast is not None:
                    time.sleep(0.05)
                    dxva2.SetMonitorContrast(h, contrast)
        except Exception as e:
            print(f"DDC/CI: {e}")

# ── Throttle ─────────────────────────────────────────────
# İlk değişikliği anında gönderir; sonraki değişiklikler THROTTLE_MS
# cooldown'ı dolduğunda (ya da pot durduğunda trailing update olarak) gönderilir.
_thr_lock      = threading.Lock()
_thr_pending_b = None
_thr_pending_c = None
_thr_last_sent = 0.0   # time.monotonic()
_thr_timer     = None

def _enqueue(b, c):
    try:
        _ddc_queue.put_nowait((b, c))
    except queue.Full:
        try:
            _ddc_queue.get_nowait()
        except queue.Empty:
            pass
        try:
            _ddc_queue.put_nowait((b, c))
        except queue.Full:
            pass

def _flush_throttle():
    global _thr_pending_b, _thr_pending_c, _thr_last_sent, _thr_timer
    with _thr_lock:
        b, c = _thr_pending_b, _thr_pending_c
        _thr_pending_b = None
        _thr_pending_c = None
        _thr_last_sent = time.monotonic()
        _thr_timer = None
    if b is not None or c is not None:
        _enqueue(b, c)

def set_monitor_throttled(brightness=None, contrast=None):
    global _thr_pending_b, _thr_pending_c, _thr_last_sent, _thr_timer
    now = time.monotonic()
    with _thr_lock:
        if brightness is not None:
            _thr_pending_b = brightness
        if contrast is not None:
            _thr_pending_c = contrast
        elapsed_ms = (now - _thr_last_sent) * 1000
        if elapsed_ms >= THROTTLE_MS:
            # Cooldown doldu — anında gönder
            b, c = _thr_pending_b, _thr_pending_c
            _thr_pending_b = None
            _thr_pending_c = None
            _thr_last_sent = now
            if _thr_timer is not None:
                _thr_timer.cancel()
                _thr_timer = None
        else:
            b, c = None, None
            # Trailing update için timer kur (sadece yoksa)
            if _thr_timer is None:
                remaining = (THROTTLE_MS - elapsed_ms) / 1000.0
                t = threading.Timer(remaining, _flush_throttle)
                t.daemon = True
                t.start()
                _thr_timer = t
    if b is not None or c is not None:
        _enqueue(b, c)

# ── OSD ─────────────────────────────────────────────────
class OSD:
    def __init__(self):
        self.hwnd       = None
        self.brightness = 50
        self.contrast   = 50
        self.mode       = "BRT"
        self._lock      = threading.Lock()
        self._hide_timer= None
        self._proc_ref  = None
        self._ready     = threading.Event()
        threading.Thread(target=self._loop, daemon=True).start()
        if not self._ready.wait(timeout=3.0):
            print("OSD thread zaman asimi")

    def _loop(self):
        hinstance = kernel32.GetModuleHandleW(None)

        def wnd_proc(hwnd, msg, wparam, lparam):
            if msg == 0x0002:
                user32.PostQuitMessage(0)
                return 0
            if msg == 0x000F:
                self._paint(hwnd)
                return 0
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        self._proc_ref = WNDPROCTYPE(wnd_proc)

        wc = WNDCLASSEXW()
        wc.cbSize        = sizeof(WNDCLASSEXW)
        wc.lpfnWndProc   = self._proc_ref
        wc.hInstance     = hinstance
        wc.hCursor       = user32.LoadCursorW(None, ctypes.cast(32512, wintypes.LPCWSTR))
        wc.hbrBackground = None
        wc.lpszClassName = CLASS_NAME

        atom = user32.RegisterClassExW(byref(wc))
        if not atom:
            err = kernel32.GetLastError()
            if err != 1410:
                print(f"RegisterClassEx basarisiz: {err}")
                self._ready.set()
                return

        sw = user32.GetSystemMetrics(0)
        sh = user32.GetSystemMetrics(1)
        W, H = 300, 88
        self.hwnd = user32.CreateWindowExW(
            WS_EX_ALL, CLASS_NAME, "", WS_POPUP,
            sw - W - 60, sh - H - 80, W, H,
            None, None, hinstance, None
        )

        if not self.hwnd:
            print(f"CreateWindowEx basarisiz: {kernel32.GetLastError()}")
            self._ready.set()
            return

        user32.SetLayeredWindowAttributes(
            self.hwnd, wintypes.COLORREF(CHROMA_KEY),
            ctypes.c_byte(230), wintypes.DWORD(LWA_ALPHA | LWA_COLORKEY)
        )
        print("OSD penceresi hazir.")
        self._ready.set()

        msg = wintypes.MSG()
        while user32.GetMessageW(byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(byref(msg))
            user32.DispatchMessageW(byref(msg))

    def _paint(self, hwnd):
        ps  = PAINTSTRUCT()
        hdc = user32.BeginPaint(hwnd, byref(ps))

        rc = wintypes.RECT()
        user32.GetClientRect(hwnd, byref(rc))
        W = rc.right

        def fill(r, color):
            b = gdi32.CreateSolidBrush(wintypes.COLORREF(color))
            user32.FillRect(hdc, byref(r), b)
            gdi32.DeleteObject(b)

        fill(rc, CHROMA_KEY)
        fill(wintypes.RECT(6, 6, W-6, 82), COLOR_BG)

        pen = gdi32.CreatePen(0, 2, wintypes.COLORREF(COLOR_GREEN))
        op  = gdi32.SelectObject(hdc, pen)
        ob  = gdi32.SelectObject(hdc, gdi32.GetStockObject(5))
        gdi32.Rectangle(hdc, 6, 6, W-6, 82)
        gdi32.SelectObject(hdc, op)
        gdi32.SelectObject(hdc, ob)
        gdi32.DeleteObject(pen)

        gdi32.SetBkMode(hdc, 1)
        gdi32.SetTextColor(hdc, wintypes.COLORREF(COLOR_GREEN))

        val = self.brightness if self.mode == "BRT" else self.contrast

        def font(h, w):
            lf = LOGFONTW()
            lf.lfHeight   = h
            lf.lfWeight   = w
            lf.lfFaceName = "Terminus"
            return gdi32.CreateFontIndirectW(byref(lf))

        f1 = font(-15, 700)
        of = gdi32.SelectObject(hdc, f1)
        user32.DrawTextW(hdc,
            "BRIGHTNESS" if self.mode == "BRT" else "CONTRAST  ",
            -1, byref(wintypes.RECT(16, 12, W-88, 34)), 0)

        f2 = font(-28, 900)
        gdi32.SelectObject(hdc, f2)
        user32.DrawTextW(hdc, f"{val:3d}", -1,
            byref(wintypes.RECT(W-84, 8, W-12, 46)), 2)
        gdi32.DeleteObject(f2)
        gdi32.SelectObject(hdc, of)
        gdi32.DeleteObject(f1)

        BY, BH = 52, 16
        fill(wintypes.RECT(16, BY, W-16, BY+BH), 0x00111111)
        fw = max(2, int((W-32) * val / 100))
        fill(wintypes.RECT(16, BY, 16+fw, BY+BH), COLOR_GREEN)

        sp = gdi32.CreatePen(0, 1, wintypes.COLORREF(COLOR_BG))
        op = gdi32.SelectObject(hdc, sp)
        for i in range(1, 10):
            tx = 16 + int((W-32) * i / 10)
            gdi32.MoveToEx(hdc, tx, BY, None)
            gdi32.LineTo(hdc, tx, BY+BH)
        gdi32.SelectObject(hdc, op)
        gdi32.DeleteObject(sp)

        user32.EndPaint(hwnd, byref(ps))

    def show(self, mode, brightness, contrast):
        with self._lock:
            self.mode       = mode
            self.brightness = brightness
            self.contrast   = contrast
        if not self.hwnd:
            return
        user32.ShowWindow(self.hwnd, 5)
        user32.InvalidateRect(self.hwnd, None, True)
        user32.UpdateWindow(self.hwnd)
        if self._hide_timer:
            self._hide_timer.cancel()
        t = threading.Timer(2.0, lambda: user32.ShowWindow(self.hwnd, 0))
        t.daemon = True
        t.start()
        self._hide_timer = t

def connect_device():
    dev = hid.device()
    print("CH552 bekleniyor...")
    while True:
        try:
            dev.open(VENDOR_ID, PRODUCT_ID)
            dev.set_nonblocking(True)
            print("CH552 baglandi.")
            return dev
        except Exception:
            time.sleep(2.0)

def main():
    osd = OSD()
    if not osd.hwnd:
        print("OSD baslatılamadı.")
        return

    threading.Thread(target=_ddc_worker, daemon=True).start()

    dev = connect_device()

    prev_b, prev_c = -1, -1
    last = "BRT"

    try:
        while True:
            try:
                data = dev.read(64)
                if data and len(data) >= 2:
                    b = map_brightness(data[0])
                    c = map_contrast(data[1])
                    bc = abs(b - prev_b) >= 1
                    cc = abs(c - prev_c) >= 1
                    if bc or cc:
                        if bc: last = "BRT"
                        if cc: last = "CON"
                        set_monitor_throttled(
                            brightness=b if bc else None,
                            contrast=c if cc else None
                        )
                        osd.show(last, b, c)
                        prev_b, prev_c = b, c
                time.sleep(0.02)

            except OSError:
                print()
                print("  ╔══════════════════════════════════╗")
                print("  ║   signal lost — CH552 offline    ║")
                print("  ╚══════════════════════════════════╝")
                try:
                    dev.close()
                except Exception:
                    pass
                time.sleep(1.0)
                dev = connect_device()
                buf_b.clear()
                buf_c.clear()
                prev_b, prev_c = -1, -1

    except KeyboardInterrupt:
        print("\n  kapatiliyor...")
        try:
            dev.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()
