import ctypes
from ctypes import wintypes
import os


IS_WINDOWS = os.name == "nt"

if IS_WINDOWS:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    WM_DEVICECHANGE = 0x0219
    WM_POWERBROADCAST = 0x0218
    DBT_DEVICEARRIVAL = 0x8000
    DBT_DEVICEREMOVECOMPLETE = 0x8004
    PBT_APMPOWERSTATUSCHANGE = 0x000A
    GWL_WNDPROC = -4
    EVENT_SYSTEM_FOREGROUND = 0x0003
    WINEVENT_OUTOFCONTEXT = 0x0000
    WINEVENT_SKIPOWNPROCESS = 0x0002
    DRIVE_REMOVABLE = 2

    if ctypes.sizeof(ctypes.c_void_p) == ctypes.sizeof(ctypes.c_longlong):
        LONG_PTR = ctypes.c_longlong
    else:
        LONG_PTR = ctypes.c_long
    LRESULT = LONG_PTR

    class SYSTEM_POWER_STATUS(ctypes.Structure):
        _fields_ = [
            ("ACLineStatus", wintypes.BYTE),
            ("BatteryFlag", wintypes.BYTE),
            ("BatteryLifePercent", wintypes.BYTE),
            ("SystemStatusFlag", wintypes.BYTE),
            ("BatteryLifeTime", wintypes.DWORD),
            ("BatteryFullLifeTime", wintypes.DWORD),
        ]

    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", wintypes.LONG),
            ("top", wintypes.LONG),
            ("right", wintypes.LONG),
            ("bottom", wintypes.LONG),
        ]

    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
    user32.GetWindowRect.restype = wintypes.BOOL
    user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, LONG_PTR]
    user32.SetWindowLongPtrW.restype = LONG_PTR
    user32.CallWindowProcW.argtypes = [LONG_PTR, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.CallWindowProcW.restype = LRESULT
    user32.SetWinEventHook.argtypes = [
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HMODULE,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
    ]
    user32.SetWinEventHook.restype = wintypes.HANDLE
    user32.UnhookWinEvent.argtypes = [wintypes.HANDLE]
    user32.UnhookWinEvent.restype = wintypes.BOOL


def get_removable_drives():
    if not IS_WINDOWS:
        return set()

    drives = set()
    drive_mask = kernel32.GetLogicalDrives()
    for index, letter in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
        if not (drive_mask & (1 << index)):
            continue
        root = f"{letter}:\\"
        if kernel32.GetDriveTypeW(root) == DRIVE_REMOVABLE:
            drives.add(root)
    return drives


def get_foreground_window_title(hwnd=None):
    if not IS_WINDOWS:
        return ""
    hwnd = hwnd or user32.GetForegroundWindow()
    if not hwnd:
        return ""
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value.strip()


def get_battery_snapshot():
    if not IS_WINDOWS:
        return None

    status = SYSTEM_POWER_STATUS()
    if not kernel32.GetSystemPowerStatus(ctypes.byref(status)):
        return None
    if status.BatteryFlag == 128:
        return None
    return {
        "percent": int(status.BatteryLifePercent),
        "charging": status.ACLineStatus == 1,
    }


def get_window_rect(hwnd=None):
    if not IS_WINDOWS:
        return None
    hwnd = hwnd or user32.GetForegroundWindow()
    if not hwnd:
        return None
    rect = RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    return {
        "left": int(rect.left),
        "top": int(rect.top),
        "right": int(rect.right),
        "bottom": int(rect.bottom),
        "width": int(rect.right - rect.left),
        "height": int(rect.bottom - rect.top),
    }


def is_foreground_fullscreen(screen_width, screen_height):
    rect = get_window_rect()
    if not rect:
        return False
    return (
        rect["width"] >= max(1, screen_width - 24)
        and rect["height"] >= max(1, screen_height - 24)
    )


class WindowsEventBridge:
    def __init__(self, root, on_usb_change=None, on_power_change=None, on_foreground_change=None):
        self.root = root
        self.on_usb_change = on_usb_change
        self.on_power_change = on_power_change
        self.on_foreground_change = on_foreground_change
        self.hwnd = None
        self.old_wndproc = None
        self._wndproc_ref = None
        self._foreground_hook = None
        self._foreground_callback = None

    def install(self):
        if not IS_WINDOWS:
            return False

        self.hwnd = self.root.winfo_id()

        @ctypes.WINFUNCTYPE(
            LRESULT,
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )
        def wndproc(hwnd, msg, wparam, lparam):
            if msg == WM_DEVICECHANGE and wparam in (DBT_DEVICEARRIVAL, DBT_DEVICEREMOVECOMPLETE):
                if self.on_usb_change:
                    self.root.after(0, self.on_usb_change)
            elif msg == WM_POWERBROADCAST and wparam == PBT_APMPOWERSTATUSCHANGE:
                if self.on_power_change:
                    self.root.after(0, self.on_power_change)

            if self.old_wndproc:
                return user32.CallWindowProcW(self.old_wndproc, hwnd, msg, wparam, lparam)
            return 0

        self._wndproc_ref = wndproc
        self.old_wndproc = user32.SetWindowLongPtrW(self.hwnd, GWL_WNDPROC, LONG_PTR(ctypes.cast(wndproc, ctypes.c_void_p).value))

        @ctypes.WINFUNCTYPE(
            None,
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.HWND,
            wintypes.LONG,
            wintypes.LONG,
            wintypes.DWORD,
            wintypes.DWORD,
        )
        def foreground_callback(_hook, _event, hwnd, _object_id, _child_id, _thread_id, _time_ms):
            if self.on_foreground_change:
                title = get_foreground_window_title(hwnd)
                if title:
                    self.root.after(0, lambda current=title: self.on_foreground_change(current))

        self._foreground_callback = foreground_callback
        self._foreground_hook = user32.SetWinEventHook(
            EVENT_SYSTEM_FOREGROUND,
            EVENT_SYSTEM_FOREGROUND,
            0,
            foreground_callback,
            0,
            0,
            WINEVENT_OUTOFCONTEXT | WINEVENT_SKIPOWNPROCESS,
        )
        return True

    def uninstall(self):
        if not IS_WINDOWS:
            return
        if self._foreground_hook:
            user32.UnhookWinEvent(self._foreground_hook)
            self._foreground_hook = None
        if self.hwnd and self.old_wndproc:
            user32.SetWindowLongPtrW(self.hwnd, GWL_WNDPROC, self.old_wndproc)
            self.old_wndproc = None
