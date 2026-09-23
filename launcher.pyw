from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

from app.config_store import load_config

ROOT = Path(__file__).resolve().parent
PORT = int(load_config().get("port", 8765))
HEALTH = f"http://127.0.0.1:{PORT}/api/health"


def server_is_running() -> bool:
    try:
        with urllib.request.urlopen(HEALTH, timeout=0.35) as response:
            return response.status == 200
    except Exception:
        return False


def start_server(open_browser: bool = True) -> None:
    if server_is_running():
        if open_browser:
            webbrowser.open(f"http://127.0.0.1:{PORT}")
        return

    python_exe = Path(sys.executable)
    flags = 0
    startupinfo = None
    if os.name == "nt":
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    proc = subprocess.Popen(
        [str(python_exe), "-m", "app.server"],
        cwd=str(ROOT),
        creationflags=flags,
        startupinfo=startupinfo,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    appdata = Path(os.environ.get("APPDATA", ROOT)) / "PCMixer"
    appdata.mkdir(parents=True, exist_ok=True)
    (appdata / "server.pid").write_text(str(proc.pid), encoding="ascii")

    for _ in range(30):
        if server_is_running():
            if open_browser:
                webbrowser.open(f"http://127.0.0.1:{PORT}")
            return
        time.sleep(0.1)


if __name__ == "__main__":
    start_server(open_browser="--background" not in sys.argv[1:])
