from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class MixerApp:
    key: str
    exe: str
    name: str
    volume: int
    muted: bool
    available: bool = True
    session_count: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AudioService:
    """Small adapter around Windows Core Audio via pycaw.

    Sessions are grouped by executable, so multiple Chrome/Discord sessions behave
    like one mixer channel. On non-Windows systems a demo backend is provided so
    the web UI can still be previewed/tested.
    """

    SYSTEM_KEY = "__system_sounds__"

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.demo = os.name != "nt"
        if self.demo:
            self._demo = {
                "discord.exe": {"name": "Discord", "volume": 48, "muted": False},
                "spotify.exe": {"name": "Spotify", "volume": 63, "muted": False},
                "chrome.exe": {"name": "Chrome", "volume": 36, "muted": False},
                "demo-game.exe": {"name": "Demo Game", "volume": 78, "muted": False},
            }

    @contextmanager
    def _com(self):
        if self.demo:
            yield
            return
        from comtypes import CoInitialize, CoUninitialize
        CoInitialize()
        try:
            yield
        finally:
            try:
                CoUninitialize()
            except Exception:
                pass

    @staticmethod
    def friendly_name(exe: str) -> str:
        if not exe:
            return "Unknown"
        stem = exe[:-4] if exe.lower().endswith(".exe") else exe
        replacements = {
            "discord": "Discord",
            "spotify": "Spotify",
            "chrome": "Chrome",
            "firefox": "Firefox",
            "msedge": "Edge",
            "vlc": "VLC",
            "foobar2000": "foobar2000",
            "system sounds": "System Sounds",
        }
        return replacements.get(stem.lower(), stem)

    def list_apps(self) -> list[MixerApp]:
        with self._lock:
            if self.demo:
                return [
                    MixerApp(key=k, exe=k, name=v["name"], volume=v["volume"], muted=v["muted"])
                    for k, v in self._demo.items()
                ]

            groups: dict[str, dict[str, Any]] = {}
            with self._com():
                from pycaw.pycaw import AudioUtilities
                try:
                    sessions = AudioUtilities.GetAllSessions()
                except Exception:
                    return []

                for session in sessions:
                    try:
                        simple = session.SimpleAudioVolume
                        process = getattr(session, "Process", None)
                        if process is not None:
                            exe = process.name()
                            key = exe.casefold()
                            name = self.friendly_name(exe)
                        elif int(getattr(session, "ProcessId", -1)) == 0:
                            # Windows System Sounds has process ID 0.
                            exe = self.SYSTEM_KEY
                            key = self.SYSTEM_KEY
                            name = "System Sounds"
                        else:
                            # Usually an orphaned/expired session whose process already exited.
                            continue

                        volume = int(round(float(simple.GetMasterVolume()) * 100))
                        muted = bool(simple.GetMute())
                    except Exception:
                        continue

                    bucket = groups.setdefault(
                        key,
                        {
                            "key": key,
                            "exe": exe,
                            "name": name,
                            "volumes": [],
                            "mutes": [],
                        },
                    )
                    bucket["volumes"].append(max(0, min(100, volume)))
                    bucket["mutes"].append(muted)

            result: list[MixerApp] = []
            for bucket in groups.values():
                volumes = bucket["volumes"] or [0]
                mutes = bucket["mutes"] or [False]
                result.append(
                    MixerApp(
                        key=bucket["key"],
                        exe=bucket["exe"],
                        name=bucket["name"],
                        volume=int(round(sum(volumes) / len(volumes))),
                        muted=all(mutes),
                        session_count=len(volumes),
                    )
                )
            result.sort(key=lambda x: (x.name.casefold(), x.exe.casefold()))
            return result

    def get_app(self, exe_or_key: str) -> MixerApp | None:
        wanted = self._normalize_key(exe_or_key)
        for app in self.list_apps():
            if app.key == wanted:
                return app
        return None

    def placeholder(self, exe: str) -> MixerApp:
        return MixerApp(
            key=self._normalize_key(exe),
            exe=exe,
            name=self.friendly_name(exe),
            volume=0,
            muted=False,
            available=False,
            session_count=0,
        )

    def set_volume(self, exe_or_key: str, percent: int) -> bool:
        percent = max(0, min(100, int(percent)))
        wanted = self._normalize_key(exe_or_key)
        with self._lock:
            if self.demo:
                if wanted not in self._demo:
                    return False
                self._demo[wanted]["volume"] = percent
                return True

            changed = False
            with self._com():
                from pycaw.pycaw import AudioUtilities
                try:
                    sessions = AudioUtilities.GetAllSessions()
                except Exception:
                    return False
                for session in sessions:
                    if self._session_key(session) != wanted:
                        continue
                    try:
                        session.SimpleAudioVolume.SetMasterVolume(percent / 100.0, None)
                        changed = True
                    except Exception:
                        pass
            return changed

    def set_mute(self, exe_or_key: str, muted: bool) -> bool:
        wanted = self._normalize_key(exe_or_key)
        with self._lock:
            if self.demo:
                if wanted not in self._demo:
                    return False
                self._demo[wanted]["muted"] = bool(muted)
                return True

            changed = False
            with self._com():
                from pycaw.pycaw import AudioUtilities
                try:
                    sessions = AudioUtilities.GetAllSessions()
                except Exception:
                    return False
                for session in sessions:
                    if self._session_key(session) != wanted:
                        continue
                    try:
                        session.SimpleAudioVolume.SetMute(1 if muted else 0, None)
                        changed = True
                    except Exception:
                        pass
            return changed

    def _normalize_key(self, exe_or_key: str) -> str:
        if exe_or_key == self.SYSTEM_KEY:
            return self.SYSTEM_KEY
        return (exe_or_key or "").strip().casefold()

    def _session_key(self, session) -> str:
        try:
            process = getattr(session, "Process", None)
            if process is None:
                return self.SYSTEM_KEY
            return process.name().casefold()
        except Exception:
            return ""
