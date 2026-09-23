# PC Mixer

PC Mixer turns a phone into a touch controller for individual Windows application volumes. A small server runs on your PC, and the phone opens its mixer page over your local network. No phone app or cloud account is required.

## Features

- **Fixed** view: the last focused application with a Windows audio session, plus four applications you choose.
- **Active** view: applications currently present in the Windows audio mixer.
- Live volume and mute control. Channels assigned to the same application move together.
- Choose fixed applications from current audio sessions, or enter an executable name manually.
- Optional launch at Windows sign-in, without opening a browser.

## Requirements

- Windows 10 or 11.
- Python 3.10, 3.11, or 3.12 installed on the PC. The installer needs Python on `PATH` or available through the Windows `py` launcher.
- Internet access during the first installation to download Python packages.
- PC and phone on the same local network.

This repository contains the application source and a setup script. It does not include a `.venv`; setup creates one on each PC.

## Install

1. Install [Python 3.12 for Windows](https://www.python.org/downloads/windows/) if you do not have a supported version. Enable **Add python.exe to PATH** during installation.
2. Download this repository using **Code → Download ZIP**, then extract it to a permanent folder such as `C:\Tools\PCMixer`. You can also clone it with Git. Keep the folder in place after installation.
3. Run `Install_PC_Mixer.bat` from the extracted folder. It creates a local `.venv`, installs dependencies, creates **PC Mixer** and **Stop PC Mixer** shortcuts both on the desktop and in the application folder, and starts the server.
4. Open the PC Mixer page on the PC and click ⚙. Under **Open on phone**, use the address shown there on your phone, for example `http://192.168.1.25:8765`.

After installation, start PC Mixer with either **PC Mixer** shortcut or `Start_PC_Mixer.bat`. Use **Stop PC Mixer** to stop it. Running the installer again is not required for ordinary use.

The shortcuts intentionally target `.venv\Scripts\pythonw.exe` **inside the folder where that person installed PC Mixer**. The installer creates that environment and writes shortcuts with paths for that PC. Do not copy an installed `.venv` or `.lnk` shortcuts from another computer. If you move the installation folder, run the installer again to recreate the shortcuts; re-enable **Start with Windows** if you use it.

## Use

- Drag a fader to change the corresponding application's volume in Windows. Tap its speaker button to mute or unmute it.
- **Fixed** has five channels: one follows the last focused application that has an audio session; the other four are assigned in ⚙ settings.
- **Active** lists the audio sessions currently available to Windows Core Audio. Some applications keep a session after they stop playing sound.
- In ⚙ settings, choose an application for each fixed channel from the current session list. Existing assignments remain visible as `offline` when their session disappears. **Enter .exe manually…** lets you assign an application that is not currently in the list.
- Check **Start with Windows** and press **SAVE** to start the server automatically when you sign in to Windows. This setting is off by default and applies only to your Windows user account.

If one executable owns several Windows audio sessions, PC Mixer combines them into one channel. Moving that channel sets all its sessions to the same volume. The displayed volume is their average until then.

## Connection troubleshooting

- Check that the phone and PC are on the same LAN or Wi-Fi network.
- Windows may ask you to allow the server through its firewall. Allow **Private networks** only.
- If the phone cannot reach the page, run `Enable_LAN_Access.bat` on the PC. It adds a firewall rule for TCP port 8765 on Private networks only and may request administrator approval.
- A VPN on either device may block local traffic.

Settings are stored in `%APPDATA%\PCMixer\config.json`. PC Mixer has no authentication; use it only on a trusted local network. Do not forward port 8765 from your router or expose the running server to the Internet.

## Development

The server uses FastAPI and Windows Core Audio through `pycaw`; the UI is plain HTML, CSS, and JavaScript.

Run the tests from the project folder:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
node --test tests\test_frontend.cjs
```

Node.js is needed only for the JavaScript tests, not for using PC Mixer.
