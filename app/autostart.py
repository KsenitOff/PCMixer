from __future__ import annotations

import os
import subprocess
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "PCMixerTouch"
ROOT = Path(__file__).resolve().parent.parent


def _command() -> str:
    pythonw = ROOT / ".venv" / "Scripts" / "pythonw.exe"
    launcher = ROOT / "launcher.pyw"
    if not pythonw.is_file() or not launcher.is_file():
        raise FileNotFoundError("PC Mixer launcher or Python environment is missing")
    return subprocess.list2cmdline([str(pythonw), str(launcher), "--background"])


def is_enabled() -> bool:
    if os.name != "nt":
        return False
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, VALUE_NAME)
            return value == _command()
    except (FileNotFoundError, OSError):
        return False


def set_enabled(enabled: bool) -> None:
    if os.name != "nt":
        raise OSError("Windows autostart is unavailable on this platform")
    import winreg

    if enabled:
        command = _command()
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, command)
    else:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, VALUE_NAME)
        except FileNotFoundError:
            pass
