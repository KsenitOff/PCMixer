from __future__ import annotations

import json
import os
from pathlib import Path
from threading import RLock

_LOCK = RLock()

DEFAULT_CONFIG = {
    "port": 8765,
    "fixed_apps": [
        "Discord.exe",
        "Spotify.exe",
        "chrome.exe",
        "firefox.exe"
    ],
    "poll_ms": 450,
}


def data_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
        path = base / "PCMixer"
    else:
        path = Path.home() / ".pcmixer"
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    return data_dir() / "config.json"


def load_config() -> dict:
    with _LOCK:
        path = config_path()
        if not path.exists():
            save_config(DEFAULT_CONFIG.copy())
            return DEFAULT_CONFIG.copy()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            raw = {}
        config = DEFAULT_CONFIG.copy()
        config.update(raw if isinstance(raw, dict) else {})
        fixed = config.get("fixed_apps", [])
        if not isinstance(fixed, list):
            fixed = []
        fixed = [(str(x).strip() if x is not None else "") for x in fixed][:4]
        while len(fixed) < 4:
            fixed.append("")
        config["fixed_apps"] = fixed
        return config


def save_config(config: dict) -> None:
    with _LOCK:
        path = config_path()
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
