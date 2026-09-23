from __future__ import annotations

import os
from pathlib import Path

import psutil

path = Path(os.environ.get("APPDATA", Path.cwd())) / "PCMixer" / "server.pid"
if path.exists():
    try:
        pid = int(path.read_text(encoding="ascii").strip())
        p = psutil.Process(pid)
        if p.cmdline()[-2:] != ["-m", "app.server"] or Path(p.cwd()).resolve() != Path(__file__).resolve().parent:
            raise ValueError("Stored PID does not belong to this PC Mixer server")
        children = p.children(recursive=True)
        for process in children + [p]:
            try:
                process.terminate()
            except psutil.NoSuchProcess:
                pass
        _, alive = psutil.wait_procs(children + [p], timeout=3)
        for process in alive:
            try:
                process.kill()
            except psutil.NoSuchProcess:
                pass
    except Exception:
        pass
    try:
        path.unlink()
    except Exception:
        pass
