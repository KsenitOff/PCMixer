from __future__ import annotations

import os
from pathlib import Path
from threading import Lock

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .autostart import is_enabled as autostart_enabled, set_enabled as set_autostart
from .audio_service import AudioService
from .config_store import load_config, save_config
from .focus import get_foreground_process
from .network import lan_ipv4_addresses

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

audio = AudioService()
app = FastAPI(title="PC Mixer", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
_focus_lock = Lock()
_last_audible_focus = ""


class VolumeRequest(BaseModel):
    target: str = Field(min_length=1)
    volume: int = Field(ge=0, le=100)


class MuteRequest(BaseModel):
    target: str = Field(min_length=1)
    muted: bool


class ConfigRequest(BaseModel):
    fixed_apps: list[str]
    autostart: bool | None = None


@app.get("/")
def root():
    return FileResponse(STATIC_DIR / "index.html", headers={"Cache-Control": "no-store"})


@app.get("/manifest.json")
def manifest():
    return FileResponse(STATIC_DIR / "manifest.json", media_type="application/manifest+json")


@app.get("/api/health")
def health():
    return {"ok": True, "platform": os.name, "demo": audio.demo}


@app.get("/api/state")
def state():
    global _last_audible_focus
    config = load_config()
    apps = audio.list_apps()
    by_key = {a.key: a for a in apps}

    focused = get_foreground_process()
    if audio.demo and not focused:
        focused = {"pid": 0, "exe": "demo-game.exe", "name": "Demo Game"}

    current_key = (focused.get("exe") or "").casefold() if focused else ""
    with _focus_lock:
        if current_key in by_key:
            _last_audible_focus = current_key
        selected_key = current_key if current_key in by_key else _last_audible_focus
        if selected_key not in by_key:
            selected_key = ""

    if selected_key:
        foreground = by_key[selected_key]
        foreground_dict = foreground.to_dict()
        foreground_dict["role"] = "FOCUS"
    else:
        foreground_dict = {
            "key": "",
            "exe": "",
            "name": "No focused app",
            "volume": 0,
            "muted": False,
            "available": False,
            "session_count": 0,
            "role": "FOCUS",
        }

    fixed = [foreground_dict]
    for exe in config["fixed_apps"]:
        exe = (exe or "").strip()
        if not exe:
            item = audio.placeholder("")
            item.name = "Not assigned"
        else:
            item = by_key.get(exe.casefold()) or audio.placeholder(exe)
        d = item.to_dict()
        d["role"] = "FIXED"
        fixed.append(d)

    active = []
    for a in apps:
        d = a.to_dict()
        d["role"] = "ACTIVE"
        active.append(d)

    port = int(config.get("port", 8765))
    return {
        "fixed": fixed,
        "active": active,
        "fixed_config": config["fixed_apps"],
        "available_exes": sorted({a.exe for a in apps if a.exe and a.exe != AudioService.SYSTEM_KEY}, key=str.casefold),
        "poll_ms": int(config.get("poll_ms", 450)),
        "lan_urls": [f"http://{ip}:{port}" for ip in lan_ipv4_addresses()],
        "demo": audio.demo,
        "autostart": autostart_enabled(),
    }


@app.post("/api/volume")
def set_volume(req: VolumeRequest):
    if not audio.set_volume(req.target, req.volume):
        raise HTTPException(status_code=404, detail="Audio session is not currently available")
    return {"ok": True}


@app.post("/api/mute")
def set_mute(req: MuteRequest):
    if not audio.set_mute(req.target, req.muted):
        raise HTTPException(status_code=404, detail="Audio session is not currently available")
    return {"ok": True}


@app.post("/api/config")
def set_config(req: ConfigRequest):
    if req.autostart is not None:
        try:
            set_autostart(req.autostart)
        except OSError as exc:
            raise HTTPException(status_code=500, detail="Could not change Windows startup setting") from exc
    config = load_config()
    fixed = [(x or "").strip() for x in req.fixed_apps][:4]
    while len(fixed) < 4:
        fixed.append("")
    config["fixed_apps"] = fixed
    save_config(config)
    return {"ok": True, "fixed_apps": fixed, "autostart": autostart_enabled()}


def main() -> None:
    config = load_config()
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(config.get("port", 8765)),
        log_level="warning",
        reload=False,
    )


if __name__ == "__main__":
    main()
