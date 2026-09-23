from __future__ import annotations

import ctypes
import os
from ctypes import wintypes

import psutil


def get_foreground_process() -> dict | None:
    """Return {'pid', 'exe', 'name'} for the foreground window, or None."""
    if os.name != "nt":
        return None
    try:
        user32 = ctypes.windll.user32
        get_foreground_window = user32.GetForegroundWindow
        get_foreground_window.restype = wintypes.HWND
        hwnd = get_foreground_window()
        if not hwnd:
            return None
        pid = wintypes.DWORD()
        get_window_process = user32.GetWindowThreadProcessId
        get_window_process.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
        get_window_process.restype = wintypes.DWORD
        get_window_process(hwnd, ctypes.byref(pid))
        if not pid.value:
            return None
        process = psutil.Process(pid.value)
        exe = process.name()
        return {
            "pid": pid.value,
            "exe": exe,
            "name": _friendly_name(exe),
        }
    except (psutil.Error, OSError, AttributeError):
        return None


def _friendly_name(exe: str) -> str:
    if not exe:
        return "Unknown"
    stem = exe[:-4] if exe.lower().endswith(".exe") else exe
    replacements = {
        "discord": "Discord",
        "spotify": "Spotify",
        "chrome": "Chrome",
        "firefox": "Firefox",
        "msedge": "Edge",
        "steamwebhelper": "Steam",
    }
    return replacements.get(stem.lower(), stem)
