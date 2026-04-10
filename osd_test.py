import time, threading, ctypes, ctypes.wintypes as wintypes
from ctypes import windll, byref, sizeof

user32   = windll.user32
gdi32    = windll.gdi32
kernel32 = windll.kernel32

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
user32.RegisterClassExW.restype = ctypes.c_ushort
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

WS_POPUP         = 0x80000000
WS_EX_LAYERED    = 0x00080000
WS_EX_TRANSPARENT= 0x00000020
WS_EX_TOPMOST    = 0x00000008
WS_EX_NOACTIVATE = 0x08000000
WS_EX_ALL        = WS_EX_LAYERED|WS_EX_TRANSPARENT|WS_EX_TOPMOST|WS_EX_NOACTIVATE
LWA_ALPHA        = 0x00000002
LWA_COLORKEY     = 0x00000001
COLOR_BG         = 0x001a1a1a
COLOR_GREEN      = 0x0033ff33
CHROMA_KEY       = 0x00ff00ff
CLASS_NAME       = "PVM_OSD_V3"

class OSD:
    def __init__(self):
        self.hwnd        = None
        self.brightness  = 50
        self.contrast    = 50
        self.mode        = "BRT"
        self._lock       = threading.Lock()
        self._hide_timer = None
        self._proc_ref   = None
        self._ready      = threading.Event()
        threading.Thread(target=self._loop, daemon=True).start()
        if not self._ready.wait(timeout=3.0):
            print("OSD thread zaman aşımı")

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
                print(f"RegisterClassEx başarısız: {err}")
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
            print(f"CreateWindowEx başarısız: {kernel32.GetLastError()}")
            self._ready.set()
            return

        user32.SetLayeredWindowAttributes(
            self.hwnd, wintypes.COLORREF(CHROMA_KEY),
            ctypes.c_byte(230), wintypes.DWORD(LWA_ALPHA | LWA_COLORKEY)
        )
        print("OSD penceresi hazır.")
        self._ready.set()

        msg = wintypes.MSG()
        while user32.GetMessageW(byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(byref(msg))
            user32.DispatchMessageW(byref(msg))

    def _paint(self, hwnd):
        ps  = PAINTSTRUCT()
        hdc = user32.BeginPaint(hwnd, byref(ps))
        rc  = wintypes.RECT()
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
            lf.lfFaceName = "Courier New"
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

# ── TEST: pot simülasyonu ────────────────────────────────
if __name__ == "__main__":
    osd = OSD()
    if not osd.hwnd:
        print("OSD başlatılamadı.")
        exit(1)

    print("Test başlıyor — pot hareketi simüle ediliyor.")
    print("Ctrl+C ile durdur.\n")

    # Brightness: 0'dan 100'e çık, sonra in
    for val in list(range(0, 101, 5)) + list(range(100, -1, -5)):
        print(f"BRT={val:3d}")
        osd.show("BRT", val, 50)
        time.sleep(0.15)

    time.sleep(1.0)

    # Contrast: 0'dan 100'e çık
    for val in list(range(0, 101, 5)) + list(range(100, -1, -5)):
        print(f"CON={val:3d}")
        osd.show("CON", 75, val)
        time.sleep(0.15)

    print("\nTest tamamlandı. 3 saniye sonra kapanıyor...")
    time.sleep(3)
