import ctypes
import ctypes.wintypes as wintypes

dxva2 = ctypes.windll.dxva2
user32 = ctypes.windll.user32

PHYSICAL_MONITOR_DESCRIPTION_SIZE = 128

class PHYSICAL_MONITOR(ctypes.Structure):
    _fields_ = [
        ("hPhysicalMonitor", wintypes.HANDLE),
        ("szPhysicalMonitorDescription", ctypes.c_wchar * PHYSICAL_MONITOR_DESCRIPTION_SIZE)
    ]

monitors = []

def monitor_enum_proc(hMonitor, hdcMonitor, lprcMonitor, dwData):
    count = wintypes.DWORD(0)
    dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR(hMonitor, ctypes.byref(count))
    phys = (PHYSICAL_MONITOR * count.value)()
    dxva2.GetPhysicalMonitorsFromHMONITOR(hMonitor, count.value, phys)
    for m in phys:
        monitors.append(m.hPhysicalMonitor)
    return True

MonitorEnumProc = ctypes.WINFUNCTYPE(
    wintypes.BOOL,
    wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM
)

user32.EnumDisplayMonitors(None, None, MonitorEnumProc(monitor_enum_proc), 0)

for h in monitors:
    min_c = wintypes.DWORD(0)
    cur_c = wintypes.DWORD(0)
    max_c = wintypes.DWORD(0)
    ok = dxva2.GetMonitorContrast(h, ctypes.byref(min_c), ctypes.byref(cur_c), ctypes.byref(max_c))
    print(f"Contrast: min={min_c.value} cur={cur_c.value} max={max_c.value} ok={ok}")
    dxva2.SetMonitorContrast(h, 50)
    print("SetMonitorContrast(50) gonderildi")
    dxva2.DestroyPhysicalMonitor(h)