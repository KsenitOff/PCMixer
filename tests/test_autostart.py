import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from app import autostart, server


class FakeWinreg:
    HKEY_CURRENT_USER = object()
    KEY_SET_VALUE = 1
    REG_SZ = 1

    def __init__(self):
        self.values = {}

    def CreateKeyEx(self, root, path, reserved, access):
        return self

    def OpenKey(self, root, path, reserved=0, access=0):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def SetValueEx(self, key, name, reserved, kind, value):
        self.values[name] = value

    def QueryValueEx(self, key, name):
        if name not in self.values:
            raise FileNotFoundError(name)
        return self.values[name], self.REG_SZ

    def DeleteValue(self, key, name):
        if name not in self.values:
            raise FileNotFoundError(name)
        del self.values[name]


class AutostartTests(unittest.TestCase):
    def test_toggle_only_our_run_entry(self):
        fake = FakeWinreg()
        fake.values["OtherProgram"] = "untouched"
        with patch.object(autostart, "os", types.SimpleNamespace(name="nt")), patch.dict(sys.modules, {"winreg": fake}), patch.object(autostart, "_command", return_value='"pythonw.exe" "launcher.pyw" --background'):
            self.assertFalse(autostart.is_enabled())
            autostart.set_enabled(True)
            self.assertTrue(autostart.is_enabled())
            autostart.set_enabled(False)
            self.assertFalse(autostart.is_enabled())
        self.assertEqual(fake.values, {"OtherProgram": "untouched"})

    def test_config_request_changes_autostart_only_when_supplied(self):
        config = {"fixed_apps": ["a.exe", "", "", ""]}
        with patch.object(server, "load_config", return_value=config), patch.object(server, "save_config") as save, patch.object(server, "set_autostart") as toggle, patch.object(server, "autostart_enabled", return_value=False):
            server.set_config(server.ConfigRequest(fixed_apps=["chrome.exe"]))
            toggle.assert_not_called()
            server.set_config(server.ConfigRequest(fixed_apps=["chrome.exe"], autostart=True))
            toggle.assert_called_once_with(True)
            self.assertEqual(save.call_count, 2)

    def test_background_launcher_does_not_open_browser(self):
        launcher_path = Path(__file__).resolve().parent.parent / "launcher.pyw"
        from importlib.machinery import SourceFileLoader
        spec = importlib.util.spec_from_loader("pcmixer_launcher", SourceFileLoader("pcmixer_launcher", str(launcher_path)))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.object(module, "server_is_running", return_value=True), patch.object(module.webbrowser, "open") as browser:
            module.start_server(open_browser=False)
            browser.assert_not_called()


if __name__ == "__main__":
    unittest.main()
