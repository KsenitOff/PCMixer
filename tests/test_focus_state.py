import unittest
from unittest.mock import patch

from app import server
from app.audio_service import MixerApp


class FocusStateTests(unittest.TestCase):
    def setUp(self):
        server._last_audible_focus = ""
        self.apps = [
            MixerApp("chrome.exe", "chrome.exe", "Chrome", 42, False),
            MixerApp("discord.exe", "Discord.exe", "Discord", 73, True),
        ]
        self.mocks = [
            patch.object(server.audio, "list_apps", side_effect=lambda: self.apps),
            patch.object(server.audio, "demo", False),
            patch.object(server, "load_config", return_value={"fixed_apps": ["chrome.exe", "", "", ""], "port": 8765, "poll_ms": 450}),
            patch.object(server, "lan_ipv4_addresses", return_value=[]),
            patch.object(server, "autostart_enabled", return_value=False),
        ]
        for mock in self.mocks:
            mock.start()

    def tearDown(self):
        for mock in reversed(self.mocks):
            mock.stop()

    def focus(self, exe):
        with patch.object(server, "get_foreground_process", return_value={"exe": exe} if exe else None):
            return server.state()["fixed"][0]

    def test_focus_stays_on_last_app_with_audio(self):
        self.assertEqual(self.focus("explorer.exe")["key"], "")
        self.assertEqual(self.focus("chrome.exe")["key"], "chrome.exe")
        self.assertEqual(self.focus("explorer.exe")["key"], "chrome.exe")
        self.assertEqual(self.focus("Discord.exe")["key"], "discord.exe")
        self.assertEqual(self.focus(None)["key"], "discord.exe")

    def test_disappeared_session_is_not_kept_as_active_focus(self):
        self.focus("chrome.exe")
        self.apps = [self.apps[1]]
        self.assertEqual(self.focus("explorer.exe")["key"], "")

    def test_current_audio_values_are_returned_on_each_poll(self):
        self.focus("chrome.exe")
        self.apps[0].volume = 17
        self.apps[0].muted = True
        focused = self.focus("explorer.exe")
        self.assertEqual((focused["volume"], focused["muted"]), (17, True))


if __name__ == "__main__":
    unittest.main()
